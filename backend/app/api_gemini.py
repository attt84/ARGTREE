"""ライブ議論木機能のLLM処理（ツリー生成・深掘り解説・クエリ拡張）。

すべて google-genai の構造化出力（response_schema）を使い、手動JSONパースは行わない。
"""
import logging

from .llm import agenerate_structured, agenerate_text
from .models import ArgumentTree, ExpandedQueries

logger = logging.getLogger(__name__)


async def generate_argument_tree(query: str, minutes_text: str) -> ArgumentTree:
    """議事録テキストを解析し、議論木（Argument Tree）として構造化する。"""
    prompt = f"""
あなたは議論を整理・構造化する専門AI（国会議論木）です。
以下の国会議事録テキスト（キーワードに関する発言の抜粋）を分析し、テーマ「{query}」に関する議論木（Argument Tree）を生成してください。

【議事録】
{minutes_text}

【構造化のルール】
- nodeのlabelは意見や論点の短い要約（20文字以内）
- nodeのtypeは "theme"（大テーマ）, "pro"（賛成意見）, "con"（反対意見）, "neutral"（中立/補足）, "solution"（解決策/提案）のいずれか
- nodeのsourceには発言者名を入れる（わかれば）
- 必ずルートノード（type: "theme"）を1つ作成し、そこから派生するように pro, con, neutral, solution をエッジでつなぐ
- ノードは8〜20個程度。議事録に実際に存在する論点のみを使い、創作しない
- edgeのsource/targetにはnodeのidを指定する
"""
    tree = await agenerate_structured(prompt, ArgumentTree, temperature=0.2)
    # 構造の妥当性チェック: 存在しないノードを指すエッジを除去する
    node_ids = {n.id for n in tree.nodes}
    tree.edges = [e for e in tree.edges if e.source in node_ids and e.target in node_ids]
    return tree


async def generate_node_detail(query: str, node_label: str, minutes_text: str) -> str:
    """特定の論点についての深掘り解説をMarkdownで生成する。"""
    prompt = f"""
あなたは議論を深掘りして解説する専門AI（国会議論木）です。
以下の国会議事録テキスト（テーマ「{query}」に関する発言）をもとに、特定の論点である「{node_label}」について詳細な解説をMarkdown形式で生成してください。

【要求事項】
1. **背景と詳細**: なぜこの論点が挙がっているのか、具体的な背景を2〜3段落で説明してください。
2. **関連する発言の引用**: 議事録の中から、この論点に最も関連する発言（発言者名と内容の要約や引用）をピックアップして提示してください。その際、必ず提供されているURL（一次情報のリンク）も一緒に記載してください。
3. **考えられる対立意見や課題**: この論点に対する懸念や反論、今後の課題について整理してください。

【厳守事項】
- 引用・URL・発言者名は必ず議事録テキスト内に実在するものだけを使うこと。創作しないこと。

【議事録】
{minutes_text}
"""
    return await agenerate_text(prompt, temperature=0.3)


async def expand_search_query(original_query: str) -> list[str]:
    """検索クエリをAIで拡張する（超検索）。失敗時は元クエリのみ返す。"""
    prompt = f"""
あなたは政治や社会問題に関する検索クエリの拡張を行う専門アシスタントです。
ユーザーが入力したキーワード「{original_query}」に対して、国会議事録でよく一緒に議論される、あるいは関連するキーワードやフレーズを推測し、検索クエリのリストを作成してください。

【ルール】
- 検索の網羅性を高めるため、元のキーワードを含めつつ、別の視点や関連語を用いたクエリを合計3つ作成してください。
- 1つのクエリにつき、1語または2語（スペース区切りでAND検索になります）としてください。長すぎる文章は避けてください。

【例】ユーザー入力が「少子化対策」の場合: ["少子化対策", "児童手当", "育休 支援"]
"""
    try:
        result = await agenerate_structured(prompt, ExpandedQueries, temperature=0.5)
        queries = [q.strip() for q in result.queries if q.strip()]
        if not queries:
            return [original_query]
        if original_query not in queries:
            queries.insert(0, original_query)
        return queries[:3]
    except Exception as e:  # 拡張の失敗は致命的ではないため元クエリで続行する
        logger.warning("query expansion failed, falling back to original: %s", e)
        return [original_query]
