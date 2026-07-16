import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import db
from .api_gemini import expand_search_query, generate_argument_tree, generate_node_detail
from .api_kokkai import format_context, search_speeches
from .config import get_settings
from .errors import CorpusNotReadyError, ExternalAPIError, LLMError, NoResultsError
from .models import (ArgumentResponse, CorpusStatus, DeepSearchRequest,
                     DeepSearchResponse, NodeDetailRequest, NodeDetailResponse,
                     SearchRequest)
from .multihop import deep_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.gemini_api_key:
        # fail fast: キーなしで起動しても全機能が壊れるため即座に気づけるようにする
        raise RuntimeError("GEMINI_API_KEY が設定されていません（backend/.env を確認してください）")
    db.init_db()
    yield


app = FastAPI(title="国会議論木 API", description="議事録を構造化・可視化するAPI",
              lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 例外ハンドラ: 内部詳細はログにのみ残し、フロントには固定メッセージを返す ----

@app.exception_handler(ExternalAPIError)
async def external_api_error_handler(request: Request, exc: ExternalAPIError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(NoResultsError)
async def no_results_handler(request: Request, exc: NoResultsError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(CorpusNotReadyError)
async def corpus_not_ready_handler(request: Request, exc: CorpusNotReadyError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "サーバー内部でエラーが発生しました。しばらくして再試行してください"},
    )


# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"message": "Welcome to 国会議論木 API"}


@app.post("/api/search", response_model=ArgumentResponse)
async def search_and_structure(request: SearchRequest):
    """キーワードで国会議事録をライブ検索し、Geminiで議論木として構造化して返す。"""
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="キーワードを入力してください")

    queries = await expand_search_query(query) if request.use_super_search else [query]

    settings = get_settings()
    per_query = max(5, settings.live_max_records // len(queries))
    speeches = await search_speeches(queries, per_query=per_query)
    if not speeches:
        raise NoResultsError("該当する議事録が見つかりませんでした。キーワードを変えてお試しください")

    minutes_text = format_context(speeches)
    tree = await generate_argument_tree(query, minutes_text)
    return ArgumentResponse(query=query, expanded_queries=queries, tree=tree)


@app.post("/api/node_detail", response_model=NodeDetailResponse)
async def get_node_detail(request: NodeDetailRequest):
    """特定のノードに関する詳細な解説（RAG）を生成する。"""
    if not request.query.strip() or not request.node_label.strip():
        raise HTTPException(status_code=400, detail="クエリとノードラベルを指定してください")

    speeches = await search_speeches([request.query],
                                     per_query=get_settings().live_max_records)
    if not speeches:
        raise NoResultsError("該当する議事録が見つかりませんでした")

    minutes_text = format_context(speeches)
    detail_markdown = await generate_node_detail(request.query, request.node_label,
                                                 minutes_text)
    return NodeDetailResponse(node_label=request.node_label,
                              detail_markdown=detail_markdown)


@app.post("/api/deep_search", response_model=DeepSearchResponse)
async def deep_search_endpoint(request: DeepSearchRequest):
    """コーパスDB上で関連事象を多段に手繰るマルチホップ検索を実行する。"""
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="問いを入力してください")
    return await deep_search(query, max_hops=request.max_hops)


@app.get("/api/corpus_status", response_model=CorpusStatus)
def get_corpus_status():
    """コーパスDBの構築状態を返す。"""
    db.init_db()
    with db.db_conn() as conn:
        return CorpusStatus(**db.corpus_status(conn))
