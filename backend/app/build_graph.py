"""明示参照グラフの構築CLI。

発言テキストから法案・法律・事件・制度などの固有名をルールベースで抽出し、
entities（ノード）と mentions（発言→エンティティのエッジ）を構築する。
LLMを使わないため何度でも無コストで再実行できる（実行のたびに全再構築）。

使い方:
    python -m app.build_graph
"""
import logging
import re
import unicodedata
from collections import Counter

from . import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# 接頭の指示語・修飾語（「同法」「本法案」など）は正規化のため除去する
LEADING_ANAPHORA = re.compile(r"^(?:同|本|当|該|当該|新|旧|現行|改正)")

PATTERNS: list[tuple[str, re.Pattern]] = [
    # 法案（〜法案・〜法律案）
    ("bill", re.compile(r"[一-龠々〇ヵヶァ-ヴーA-Za-z0-9]{1,24}(?:法律案|法案)")),
    # 法律（〜法）
    ("law", re.compile(r"[一-龠々〇ヵヶァ-ヴーA-Za-z0-9]{1,24}法(?![律案人的令規化廷曹科学問])")),
    # 事象（〜事件・〜事故・〜疑惑・〜危機など）
    ("event", re.compile(r"[一-龠々〇ヵヶァ-ヴーA-Za-z0-9]{2,20}(?:事件|事故|疑惑|不祥事|危機|ショック|震災|災害)")),
    # 制度・税
    ("system", re.compile(r"[一-龠々〇ヵヶァ-ヴーA-Za-z0-9]{2,20}(?:制度|税)")),
]

# 一般語としての誤検出を除外する
STOPWORDS = {
    "方法", "手法", "文法", "語法", "用法", "作法", "寸法", "論法", "魔法",
    "療法", "工法", "無法", "違法", "合法", "遵法", "適法", "不法", "司法",
    "立法", "税法",  # 税法単独は一般語に近い
    "諸問題",
    # 接尾語のみ・指示語つきの汎用形（固有名を持たないため手繰り先として無意味）
    "法案", "法律案", "事件", "事故", "制度", "課税", "減税", "増税",
    "両法案", "同法案", "本法案", "各法案", "一法", "全法案", "関係法",
    "整備法", "改正法", "特別法", "一般法", "既存法",
}
# 2文字の「〜法」は誤検出が多いため、実在する主要法典のみ許可する
TWO_CHAR_LAW_ALLOWLIST = {"憲法", "民法", "刑法", "商法"}


def extract_entities(text: str) -> Counter:
    """発言テキストから (type, label) → 出現回数 を抽出する。"""
    text = unicodedata.normalize("NFKC", text)
    counts: Counter = Counter()
    for entity_type, pattern in PATTERNS:
        for match in pattern.findall(text):
            label = LEADING_ANAPHORA.sub("", match)
            if len(label) < 2 or label in STOPWORDS:
                continue
            if entity_type == "law" and len(label) == 2 and label not in TWO_CHAR_LAW_ALLOWLIST:
                continue
            counts[(entity_type, label)] += 1
    return counts


def main() -> None:
    db.init_db()
    with db.db_conn() as conn:
        conn.execute("DELETE FROM mentions")
        conn.execute("DELETE FROM entities")

        entity_ids: dict[tuple[str, str], int] = {}
        processed = 0
        mention_rows = 0

        cursor = conn.execute("SELECT speech_id, speech FROM speeches")
        while True:
            batch = cursor.fetchmany(1000)
            if not batch:
                break
            for row in batch:
                counts = extract_entities(row["speech"] or "")
                for (entity_type, label), count in counts.items():
                    key = (entity_type, label)
                    if key not in entity_ids:
                        cur = conn.execute(
                            "INSERT OR IGNORE INTO entities (type, label) VALUES (?, ?)",
                            key,
                        )
                        entity_ids[key] = cur.lastrowid or conn.execute(
                            "SELECT entity_id FROM entities WHERE type=? AND label=?", key
                        ).fetchone()[0]
                    conn.execute(
                        "INSERT OR REPLACE INTO mentions (speech_id, entity_id, count) VALUES (?, ?, ?)",
                        (row["speech_id"], entity_ids[key], count),
                    )
                    mention_rows += 1
            processed += len(batch)
            logger.info("processed %d speeches (%d entities, %d mentions)",
                        processed, len(entity_ids), mention_rows)

        top = conn.execute(
            """SELECT e.type, e.label, COUNT(*) AS n FROM mentions m
               JOIN entities e ON e.entity_id = m.entity_id
               GROUP BY m.entity_id ORDER BY n DESC LIMIT 15"""
        ).fetchall()
        logger.info("done. top entities:")
        for row in top:
            logger.info("  [%s] %s (%d speeches)", row["type"], row["label"], row["n"])


if __name__ == "__main__":
    main()
