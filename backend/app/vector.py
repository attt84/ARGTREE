"""埋め込みベクトルの保存とコサイン類似検索。

インデックスはSQLiteのBLOB（float32）として保存し、検索時にメモリへ
行列としてロードする（数十万件まではブルートフォースで実用十分）。
"""
import logging
import sqlite3
import struct

import numpy as np

from .config import get_settings
from .llm import embed_texts

logger = logging.getLogger(__name__)

# 埋め込み対象テキストの上限文字数（長い演説の冒頭部分で意味は十分捉えられる）
EMBED_CHAR_LIMIT = 2000

_matrix_cache: dict = {"count": -1, "ids": None, "matrix": None}


def vector_to_blob(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def blob_to_vector(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def store_embeddings(conn: sqlite3.Connection, speech_ids: list[str],
                     vectors: list[list[float]]) -> None:
    settings = get_settings()
    conn.executemany(
        "INSERT OR REPLACE INTO embeddings (speech_id, model, dim, vector) VALUES (?, ?, ?, ?)",
        [
            (sid, settings.embedding_model, len(vec), vector_to_blob(vec))
            for sid, vec in zip(speech_ids, vectors)
        ],
    )


def _load_matrix(conn: sqlite3.Connection):
    """全埋め込みを (ids, 正規化済み行列) としてロードする。件数が変わるまでキャッシュ。"""
    count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
    if count == _matrix_cache["count"]:
        return _matrix_cache["ids"], _matrix_cache["matrix"]
    if count == 0:
        _matrix_cache.update(count=0, ids=[], matrix=None)
        return [], None
    rows = conn.execute("SELECT speech_id, vector FROM embeddings").fetchall()
    ids = [r["speech_id"] for r in rows]
    matrix = np.vstack([blob_to_vector(r["vector"]) for r in rows])
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix = matrix / norms
    _matrix_cache.update(count=count, ids=ids, matrix=matrix)
    logger.info("loaded %d embeddings into memory", count)
    return ids, matrix


def vector_search(conn: sqlite3.Connection, query_text: str, limit: int = 10,
                  exclude_ids: set[str] | None = None) -> list[sqlite3.Row]:
    """クエリ文を埋め込み、コサイン類似度の高い発言を返す。索引が空なら空リスト。"""
    ids, matrix = _load_matrix(conn)
    if matrix is None:
        return []
    exclude_ids = exclude_ids or set()
    query_vec = np.array(embed_texts([query_text], task_type="RETRIEVAL_QUERY")[0],
                         dtype=np.float32)
    norm = np.linalg.norm(query_vec)
    if norm > 0:
        query_vec = query_vec / norm
    scores = matrix @ query_vec
    order = np.argsort(-scores)
    result_ids = []
    for idx in order:
        sid = ids[idx]
        if sid in exclude_ids:
            continue
        result_ids.append(sid)
        if len(result_ids) >= limit:
            break
    if not result_ids:
        return []
    placeholders = ",".join("?" for _ in result_ids)
    rows = conn.execute(
        f"SELECT * FROM speeches WHERE speech_id IN ({placeholders})", result_ids
    ).fetchall()
    by_id = {r["speech_id"]: r for r in rows}
    return [by_id[sid] for sid in result_ids if sid in by_id]
