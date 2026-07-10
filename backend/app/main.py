from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .models import SearchRequest, ArgumentResponse, NodeDetailRequest, NodeDetailResponse
from .api_kokkai import fetch_diet_minutes
from .api_gemini import generate_argument_tree, generate_node_detail, expand_search_query

# 環境変数の読み込み
load_dotenv()

app = FastAPI(title="ARGTREE API", description="議事録を構造化・可視化するAPI")

# CORSの設定（フロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to ARGTREE API"}

@app.post("/api/search", response_model=ArgumentResponse)
def search_and_structure(request: SearchRequest):
    """
    指定されたキーワードで国会議事録を検索し、Geminiで議論木として構造化して返す。
    """
    query = request.query
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    try:
        # クエリの拡張（超検索）
        search_queries = expand_search_query(query) if request.use_super_search else [query]
        
        # 1. 国会議事録の取得
        minutes_text = fetch_diet_minutes(search_queries)
        
        # 2. Geminiによる構造化
        tree = generate_argument_tree(query, minutes_text)
        
        return ArgumentResponse(query=query, tree=tree)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/node_detail", response_model=NodeDetailResponse)
def get_node_detail(request: NodeDetailRequest):
    """
    特定のノードに関する詳細な解説（RAG）を生成する。
    """
    if not request.query or not request.node_label:
        raise HTTPException(status_code=400, detail="Query and node_label cannot be empty")
        
    try:
        # 議事録を再取得（またはキャッシュから）
        minutes_text = fetch_diet_minutes(request.query)
        
        # 詳細レポートの生成
        detail_markdown = generate_node_detail(request.query, request.node_label, minutes_text)
        
        return NodeDetailResponse(node_label=request.node_label, detail_markdown=detail_markdown)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
