# ARGTREE (アギュドラシル)

国会の議事録等の複雑な議論を、LLM（大規模言語モデル）を用いて体系化し、「議論木（Argument Tree）」として可視化するWEBアプリケーションです。

## 概要

本プロジェクトは、「散在し消費される議論」を「構造化された資産」へと昇華させるコンセプト「argdrasill」のプロトタイプ実装です。
ユーザーがキーワードを入力すると、国会会議録検索システムAPIから関連する議事録を取得し、Gemini APIを用いて「論点」「賛成意見」「反対意見」などに分類・構造化。React Flowを用いて直感的なツリー状のUIで可視化します。

## 主な機能
- **国会議事録の自動取得**: 国会会議録検索システムAPIとの連携
- **LLMによる議論の構造化**: Gemini APIを用いた長文テキストの解析と論理関係の抽出
- **議論木の可視化**: React Flowを活用したインタラクティブなツリーUI

## 技術スタック
- **Frontend**: Next.js (React), TypeScript, React Flow, Tailwind CSS
- **Backend**: Python, FastAPI, Pydantic, google-generativeai
- **API/External Services**: 国会会議録検索システムAPI, Gemini API

## ディレクトリ構成
```text
ARGTREE/
├── frontend/   # Next.js アプリケーション (UI/UX, ツリー可視化)
├── backend/    # FastAPI アプリケーション (データ取得, LLMパイプライン)
└── README.md   # プロジェクトドキュメント
```

## ローカル環境での起動手順

### 1. バックエンド (Python)
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```
`backend` ディレクトリ内に `.env` ファイルを作成し、GeminiのAPIキーを設定してください。
```env
GEMINI_API_KEY=your_api_key_here
```
サーバーを起動します（デフォルト: http://localhost:8000）。
```bash
uvicorn app.main:app --reload
```

### 2. フロントエンド (Node.js)
```bash
cd frontend
npm install
npm run dev
```
ブラウザで `http://localhost:3000` にアクセスしてアプリケーションを利用します。
