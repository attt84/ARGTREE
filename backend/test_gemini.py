import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-3.5-flash')
query = "消費税"
minutes_text = "テスト発言です。消費税には反対です。"

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

response = model.generate_content(prompt)
print("--- RAW RESPONSE ---")
print(repr(response.text))
