# ArgTree (アギュドラシル)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Next.js](https://img.shields.io/badge/Next.js-14.x-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)

**「散在し、消費される議論を体系化し、健全な対話の土壌を育てる」**

ArgTreeは、ニュース記事や国会の議事録など、テキストベースの複雑な議論をAI（LLM）を用いて解析し、「議論木（Argument Tree）」として可視化するWebアプリケーションです。単なるベクトル検索（従来のRAG）を超え、議論の構造（論点・賛成・反対・根拠）を視覚的に把握しながら、AIと対話（壁打ち）ができる「構造化RAGプラットフォーム」を目指しています。

---

## 🎯 プロジェクトの背景・目的

現代社会において、SNSやネットニュースのコメント欄、あるいはビジネス会議など、至る所で議論が交わされています。しかし、多くの場合それらは体系化されず、同じ論点の繰り返しや平行線に終始し、「消費」されて終わってしまいます。
本プロジェクトは、LLMの自然言語理解とRAG技術を応用することで、**「誰が・どのような根拠で・何に賛成/反対しているのか」** を自動で可視化し、客観的で建設的な合意形成をサポートするインフラを構築するために開発されました。

---

## ✨ 主な機能

1. **ドキュメントの自動構造化（ETLパイプライン）**
   - PDFやテキスト（例：生成AI規制に関する議事録など）を入力として受け取り、LLMが「主要な論点」「賛否」「根拠」を自動抽出します。
   - 抽出結果はJSONおよびベクトルデータベースに格納されます。
2. **議論木（Argument Tree）のインタラクティブな可視化**
   - 構造化された議論を、マインドマップ形式でWeb画面上に描画します。
   - ノードをクリックすることで、その意見の元となった文献のソース（根拠）を参照できます。
3. **議論ナビゲーターAI（構造化RAGチャット）**
   - 議論の全体像を把握したAIに対して、「この件に関する最大の反論は？」といった質問を投げかけ、対話的に思考を深める（壁打ちする）ことが可能です。

---

## 🛠 技術スタック

### フロントエンド
- **Framework**: [Next.js](https://nextjs.org/) (App Router)
- **Language**: TypeScript
- **Styling**: Vanilla CSS (CSS Modules)
- **Visualization**: React Flow / D3.js (予定)

### バックエンド / AI
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **AI Orchestration**: LangChain / LlamaIndex
- **Vector Database**: ChromaDB
- **LLM**: Google Gemini API (or OpenAI API)

---

## 🚀 開発ロードマップ

- [x] Phase 1: プロジェクト基盤の構築と設計（本READMEの作成）
- [ ] Phase 2: データ処理・RAGバックエンドの実装 (Python/FastAPI)
- [ ] Phase 3: 議論木の可視化とチャットUIの実装 (Next.js)
- [ ] Phase 4: UXのブラッシュアップとリファクタリング

---

## 💻 ローカルでのセットアップ方法 (WIP)

*※現在開発中のため、手順は変更される可能性があります。*

### 前提条件
- Node.js (v18+)
- Python (3.10+)
- LLM API Key (Gemini API 等)

### 1. リポジトリのクローン
```bash
git clone https://github.com/your-username/argtree.git
cd argtree
```

*(バックエンド・フロントエンドの起動手順は実装後に追記予定)*
