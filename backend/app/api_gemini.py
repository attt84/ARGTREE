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
    # Gemini 1.5 Flash を使用して高速な構造化処理を行う
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
あなたは議論を整理・構造化する専門AI（アギュドラシル）です。
以下の国会議事録テキストを分析し、テーマ「{query}」に関する議論木（Argument Tree）をJSON形式で生成してください。

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

議事録テキスト:
{minutes_text[:10000]} # 長すぎる場合は切り詰める

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
        logger.error(f"Error parsing with Gemini API: {e}")
        # フォールバックのダミーツリーを返す
        return ArgumentTree(
            nodes=[
                {"id": "n1", "label": f"{query} (解析エラー)", "type": "theme", "source": "system"},
                {"id": "n2", "label": "議事録が取得できませんでした", "type": "neutral", "source": "system"}
            ],
            edges=[{"id": "e1", "source": "n1", "target": "n2"}]
        )
