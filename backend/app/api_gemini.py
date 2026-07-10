import os
import json
import logging
import google.generativeai as genai
from .models import ArgumentTree

logger = logging.getLogger(__name__)

def generate_argument_tree(query: str, minutes_text: str) -> ArgumentTree:
    """
    議事録テキストをGemini APIで解析し、議論木（Argument Tree）として構造化する。
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
        
    genai.configure(api_key=api_key)
    # Gemini 3.5 Flash を使用して高速な構造化処理を行う
    model = genai.GenerativeModel('gemini-3.5-flash')
    
    # プロンプトの構築（文字数を少し余裕をもたせる）
    prompt = f"""
あなたは議論を整理・構造化する専門AI（国会議論木）です。
以下の国会議事録テキスト（キーワードに関する発言の抜粋）を分析し、テーマ「{query}」に関する議論木（Argument Tree）をJSON形式で生成してください。

【議事録】
{minutes_text[:30000]}

議論木は nodes（ノードのリスト）と edges（エッジのリスト）で構成されます。
nodeの属性:
- id: 一意の文字列 (例: "node_1")
- label: 意見や論点の短い要約 (20文字以内)
- type: "theme" (大テーマ), "pro" (賛成意見), "con" (反対意見), "neutral" (中立/補足), "solution" (解決策/提案)
- source: 発言者名（わかれば）

edgeの属性:
- id: 一意の文字列 (例: "edge_1")
- source: 接続元のnode id
- target: 接続先のnode id

必ずルートノード（type: "theme"）を1つ作成し、そこから派生するように pro, con, neutral などをエッジでつないでください。

以下のJSONフォーマットのみを出力してください（マークダウンのコードブロックは不要です）。
{{
  "nodes": [
    {{"id": "node_1", "label": "{query}", "type": "theme", "source": "system"}}
  ],
  "edges": []
}}
"""
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # JSON部分だけを抽出する簡単なパース（```json などの除去）
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        data = json.loads(text)
        return ArgumentTree(**data)
    except Exception as e:
        import traceback
        with open("gemini_error.txt", "w", encoding="utf-8") as f:
            f.write(f"Error: {str(e)}\n")
            f.write(traceback.format_exc())
        
        logger.error(f"Error parsing with Gemini API: {e}")
        # フォールバックのダミーツリーを返す
        return ArgumentTree(
            nodes=[
                {"id": "n1", "label": f"{query} (解析エラー)", "type": "theme", "source": "system"},
                {"id": "n2", "label": "議事録が取得できませんでした", "type": "neutral", "source": "system"}
            ],
            edges=[{"id": "e1", "source": "n1", "target": "n2"}]
        )

def generate_node_detail(query: str, node_label: str, minutes_text: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3.5-flash')
    
    prompt = f"""
あなたは議論を深掘りして解説する専門AI（国会議論木）です。
以下の国会議事録テキスト（テーマ「{query}」に関する発言）をもとに、特定の論点である「{node_label}」について詳細な解説をMarkdown形式で生成してください。

【要求事項】
1. **背景と詳細**: なぜこの論点が挙がっているのか、具体的な背景を2〜3段落で説明してください。
2. **関連する発言の引用**: 議事録の中から、この論点に最も関連する発言（発言者名と内容の要約や引用）をピックアップして提示してください。その際、必ず提供されているURL（一次情報のリンク）も一緒に記載してください。
3. **考えられる対立意見や課題**: この論点に対する懸念や反論、今後の課題について整理してください。

【議事録】
{minutes_text[:30000]}
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating node detail: {e}")
        return "申し訳ありません。詳細情報の生成中にエラーが発生しました。"

def expand_search_query(original_query: str) -> list[str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3.5-flash')
    
    prompt = f"""
あなたは政治や社会問題に関する検索クエリの拡張を行う専門アシスタントです。
ユーザーが入力したキーワード「{original_query}」に対して、国会議事録でよく一緒に議論される、あるいは関連するキーワードやフレーズを推測し、検索クエリのリストを作成してください。

【ルール】
- 検索の網羅性を高めるため、元のキーワードを含めつつ、別の視点や関連語を用いたクエリを3つ作成してください。
- 1つのクエリにつき、1語または2語（スペース区切りでAND検索になります）としてください。長すぎる文章は避けてください。
- JSONフォーマットのみを出力してください。マークダウンのコードブロックは不要です。

【出力例（ユーザー入力が「少子化対策」の場合）】
["少子化対策", "児童手当", "育休 支援"]

では、以下の出力フォーマットでJSON配列のみを出力してください。
"""
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        queries = json.loads(text)
        if isinstance(queries, list) and len(queries) > 0:
            return queries[:3]
        return [original_query]
    except Exception as e:
        logger.error(f"Error expanding query: {e}")
        return [original_query]
