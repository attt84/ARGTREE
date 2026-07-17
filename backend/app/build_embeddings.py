"""埋め込みインデックスの構築CLI。

まだ埋め込みのない発言を新しい日付から順に埋め込み、embeddingsテーブルに保存する。
何度でも再実行でき、そのたびに未処理分だけが追加される（インクリメンタル）。

使い方:
    python -m app.build_embeddings --limit 2000   # まず直近2000件
    python -m app.build_embeddings                # 全件（件数×コストに注意）
"""
import argparse
import logging
import time

from . import db
from .errors import LLMError
from .llm import embed_texts
from .vector import EMBED_CHAR_LIMIT, store_embeddings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 25
MAX_RETRIES = 5


def embed_with_retry(texts: list[str]) -> list[list[float]] | None:
    """レート制限等の一時エラーに指数バックオフでリトライする。失敗し続けたらNone。"""
    delay = 5.0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return embed_texts(texts)
        except LLMError as e:
            logger.warning("embed batch failed (attempt %d/%d): %s — retrying in %.0fs",
                           attempt, MAX_RETRIES, e, delay)
            time.sleep(delay)
            delay = min(delay * 2, 60)
    return None


def build_text(row) -> str:
    """埋め込み対象テキスト。会議名・発言者を先頭に置き文脈を持たせる。"""
    header = f"{row['date']} {row['meeting']} {row['speaker']}: "
    return header + (row["speech"] or "")[:EMBED_CHAR_LIMIT]


def main() -> None:
    parser = argparse.ArgumentParser(description="発言埋め込みの構築")
    parser.add_argument("--limit", type=int, default=None,
                        help="今回埋め込む件数の上限（新しい日付から順）")
    args = parser.parse_args()

    db.init_db()
    with db.db_conn() as conn:
        rows = conn.execute(
            """
            SELECT s.* FROM speeches s
            LEFT JOIN embeddings e ON e.speech_id = s.speech_id
            WHERE e.speech_id IS NULL
            ORDER BY s.date DESC
            """ + (f" LIMIT {int(args.limit)}" if args.limit else "")
        ).fetchall()
        logger.info("embedding %d speeches (batch=%d)", len(rows), BATCH_SIZE)

        done = 0
        skipped = 0
        start = time.time()
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            vectors = embed_with_retry([build_text(r) for r in batch])
            if vectors is None:
                skipped += len(batch)
                logger.error("batch permanently failed, skipping %d speeches", len(batch))
                continue
            store_embeddings(conn, [r["speech_id"] for r in batch], vectors)
            conn.commit()
            done += len(batch)
            if done % 500 < BATCH_SIZE or done == len(rows):
                rate = done / max(time.time() - start, 1)
                logger.info("embedded %d/%d (%.1f/s, skipped=%d)", done, len(rows), rate, skipped)
            time.sleep(0.5)  # レート制限への配慮

        total = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        logger.info("done. embeddings in index: %d", total)


if __name__ == "__main__":
    main()
