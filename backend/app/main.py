from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .models import SearchRequest, ArgumentResponse
from .api_kokkai import fetch_diet_minutes
from .api_gemini import generate_argument_tree

# 環境変数の読み込み
load_dotenv()

app = FastAPI(title="ARGTREE API", description="議事録を構造化・可視化するAPI")

# CORSの設定（フロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
        # 1. 国会議事録の取得
        minutes_text = fetch_diet_minutes(query)
        
        # 2. Geminiによる構造化
        tree = generate_argument_tree(query, minutes_text)
        
        return ArgumentResponse(query=query, tree=tree)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
