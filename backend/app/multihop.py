"""マルチホップ検索エンジン（エージェント型トラバーサル）。

「過去の関連事象を1つずつ手繰る」探索を、次の3チャネルの合成で実現する:
- 全文検索（FTS5）   : キーワードによる入口・各ホップの取得
- ベクトル検索       : 言い換えに強い入口・各ホップの取得（索引があれば）
- グラフ近傍         : 発言群が言及するエンティティ（法案・事件など）を候補化し、
                       エンティティ経由で別時期・別文脈の発言へジャンプする

各ホップでLLMが「分かったこと（finding）」と「次に辿る焦点（next_focus）」を
構造化出力で判断し、完了と判断するか最大ホップ数に達するまで繰り返す。
"""
import logging
import sqlite3

from . import db
from .errors import CorpusNotReadyError, NoResultsError
from .llm import agenerate_structured, agenerate_text
from .models import (DeepSearchResponse, EvidenceItem, HopDecision, HopStep)
from .vector import vector_search

logger = logging.getLogger(__name__)

EVIDENCE_PER_HOP = 8          # 各ホップでLLMに見せる発言数
EXCERPT_CHARS = 500           # LLMに見せる発言抜粋の文字数
SNIPPET_CHARS = 220           # フロントに返すスニペットの文字数


def _retrieve(conn: sqlite3.Connection, query: str, entity: str | None,
              exclude_ids: set[str]) -> list[sqlite3.Row]:
    """グラフ・FTS・ベクトルの3チャネルから証拠候補を集める。

    チャネルごとに枠を割り当てて優先順に統合する（関連度の高いチャネルから採用し、
    日付順ソートで汎用語やベクトルノイズが上位を占有するのを防ぐ）。
    """
    candidates: dict[str, sqlite3.Row] = {}

    def add(rows: list[sqlite3.Row], cap: int) -> None:
        taken = 0
        for row in rows:
            sid = row["speech_id"]
            if sid in exclude_ids or sid in candidates:
                continue
            candidates[sid] = row
            taken += 1
            if taken >= cap:
                return

    # ① 指定エンティティ（グラフのエッジを辿るホップ）
    if entity:
        add(db.speeches_by_entity(conn, entity, limit=16, exclude_ids=exclude_ids), 4)

    # ② 問い/焦点テキストに含まれるエンティティ（自然文をグラフ語彙に接続する入口）
    for label in db.entities_in_text(conn, query, limit=2):
        add(db.speeches_by_entity(conn, label, limit=12, exclude_ids=exclude_ids), 3)

    # ③ 全文検索: まず全語AND（最も特異的）、次に語ごと
    terms = [t for t in query.split() if len(t) >= 2][:4]
    if len(terms) >= 2:
        add(db.fts_search(conn, terms, limit=12, exclude_ids=exclude_ids), 3)
    for term in terms:
        add(db.fts_search(conn, term, limit=12, exclude_ids=exclude_ids), 2)

    # ④ ベクトル検索（言い換えへの耐性。索引が無ければスキップ）
    try:
        add(vector_search(conn, query, limit=12, exclude_ids=exclude_ids), 3)
    except Exception as e:  # ベクトル索引が無い・埋め込みAPI失敗は致命的でない
        logger.warning("vector channel unavailable: %s", e)

    rows = list(candidates.values())[:EVIDENCE_PER_HOP]
    # 表示・プロンプト用に日付降順で整える（採用の取捨は上の優先順で決定済み）
    return sorted(rows, key=lambda r: r["date"] or "", reverse=True)


def _evidence_block(rows: list[sqlite3.Row]) -> str:
    parts = []
    for r in rows:
        group = f"・{r['speaker_group']}" if r["speaker_group"] else ""
        parts.append(
            f"[{r['speech_id']}] {r['date']} {r['meeting']}（{r['speaker']}{group}）\n"
            f"{(r['speech'] or '')[:EXCERPT_CHARS]}\n"
        )
    return "\n".join(parts)


def _neighborhood_block(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> str:
    entities = db.entity_neighborhood(conn, [r["speech_id"] for r in rows], limit=15)
    if not entities:
        return "（エンティティ候補なし）"
    return "\n".join(
        f"- {e['label']}（{e['type']}／この証拠群で{e['local_mentions']}件言及／"
        f"コーパス全体で{e['total_mentions']}件／初出 {e['first_date']}）"
        for e in entities
    )


def _to_evidence_items(rows: list[sqlite3.Row], selected_ids: list[str]) -> list[EvidenceItem]:
    ordered = [r for r in rows if r["speech_id"] in set(selected_ids)] or rows[:3]
    return [
        EvidenceItem(
            speech_id=r["speech_id"],
            date=r["date"] or "",
            meeting=f"{r['house'] or ''} {r['meeting'] or ''}".strip(),
            speaker=r["speaker"] or "不明",
            speaker_group=r["speaker_group"],
            snippet=(r["speech"] or "")[:SNIPPET_CHARS],
            url=r["speech_url"] or "",
        )
        for r in ordered
    ]


async def deep_search(query: str, max_hops: int = 4) -> DeepSearchResponse:
    db.init_db()
    conn = db.connect()
    try:
        status = db.corpus_status(conn)
        if not status["ready"]:
            raise CorpusNotReadyError(
                "コーパスDBが未構築です。backend で "
                "`python -m app.ingest --from YYYY-MM-DD --until YYYY-MM-DD` を実行してください"
            )

        steps: list[HopStep] = []
        seen_ids: set[str] = set()
        focus_query = query
        focus_entity: str | None = None
        focus_reason = "ユーザーの問いそのものを起点に調べる"

        for hop in range(1, max_hops + 1):
            rows = _retrieve(conn, focus_query, focus_entity, seen_ids)
            if not rows:
                if hop == 1:
                    raise NoResultsError(
                        f"コーパス（{status['date_from']}〜{status['date_until']}）に"
                        f"該当する発言が見つかりませんでした"
                    )
                break
            seen_ids.update(r["speech_id"] for r in rows)

            history = "\n".join(
                f"ホップ{s.hop}（{s.focus}）: {s.finding}" for s in steps
            ) or "（まだない）"

            prompt = f"""
あなたは国会議事録を多段に手繰って調査する専門AIです。
ユーザーの問いに答えるため、発言の証拠を読み、「これまでに分かったこと」を踏まえて、次に何を調べるべきか（あるいは調査を完了できるか）を判断してください。

【ユーザーの問い】
{query}

【これまでのホップで分かったこと】
{history}

【今回のホップの焦点】
{focus_query}{f'（エンティティ: {focus_entity}）' if focus_entity else ''}

【証拠となる発言（コーパス収録範囲: {status['date_from']}〜{status['date_until']}）】
{_evidence_block(rows)}

【証拠群が言及しているエンティティ候補（グラフ近傍）】
{_neighborhood_block(conn, rows)}

【判断のルール】
- finding: 今回の証拠から新しく分かったことを2〜4文で。発言者名・日付など具体的に
- evidence_ids: findingの根拠にした発言のID（上の[...]内の文字列）
- complete: 問いに答える因果・経緯の鎖が十分つながったらtrue
- next_focus: 続ける場合、次に手繰るべき焦点。「なぜそうなったのか」「その発端は何か」と
  過去に遡る方向を優先する。エンティティ候補に有望なもの（法案名・事件名など）があれば
  entityに指定し、queryにはそのエンティティや関連語を検索語として与える
- 証拠にない事実を創作しない。証拠が薄い場合はcompleteにせず次のホップで確かめる
"""
            decision = await agenerate_structured(prompt, HopDecision, temperature=0.2)

            steps.append(HopStep(
                hop=hop,
                focus=focus_entity or focus_query,
                reason=focus_reason,
                finding=decision.finding,
                evidence=_to_evidence_items(rows, decision.evidence_ids),
            ))

            if decision.complete or not decision.next_focus:
                break
            focus_query = decision.next_focus.query
            focus_entity = decision.next_focus.entity
            focus_reason = decision.next_focus.reason

        chain_text = "\n\n".join(
            f"### ホップ{s.hop}: {s.focus}\n{s.finding}\n" + "\n".join(
                f"- {e.date} {e.meeting} {e.speaker}: {e.snippet[:120]}…（{e.url}）"
                for e in s.evidence
            )
            for s in steps
        )
        synthesis_prompt = f"""
あなたは国会議事録の調査結果をまとめる専門AIです。
以下は「{query}」という問いについて、議事録を多段に手繰って得られた調査の鎖です。
これを統合し、問いへの回答をMarkdownで作成してください。

【要求事項】
1. 冒頭に問いへの直接の答えを2〜3文で
2. 経緯・因果の流れを時系列で整理（古い事象→新しい事象の順）
3. 重要な発言の引用には発言者名と一次情報URLを必ず添える
4. 調査の鎖に含まれない事実を創作しない。不明な点は不明と明記する

【調査の鎖】
{chain_text}
"""
        synthesis = await agenerate_text(synthesis_prompt, temperature=0.3)

        return DeepSearchResponse(query=query, steps=steps, synthesis=synthesis)
    finally:
        conn.close()
