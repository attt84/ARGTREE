"""コーパス取り込みCLI。国会会議録検索APIから日付範囲の全発言を取得してDBに保存する。

使い方:
    python -m app.ingest --from 2026-01-01 --until 2026-06-30
    python -m app.ingest --from 2026-01-01 --until 2026-06-30 --max 5000  # 件数上限つき

- 100件ずつページングし、取得のたびに保存する（中断しても再実行すれば続きから埋まる）
- 既に保存済みのspeech_idはスキップされるため、同じ範囲を再実行しても重複しない
"""
import argparse
import asyncio
import logging
import time

from . import db
from .api_kokkai import iter_speeches_by_range

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def run(from_date: str, until_date: str, max_records: int | None) -> None:
    db.init_db()
    conn = db.connect()
    start = time.time()
    stats = {"fetched": 0, "inserted": 0}

    def save_batch(rows: list[dict]) -> None:
        inserted = db.upsert_speeches(conn, rows)
        conn.commit()
        stats["fetched"] += len(rows)
        stats["inserted"] += inserted
        logger.info("fetched=%d inserted=%d (last date=%s)",
                     stats["fetched"], stats["inserted"],
                     rows[-1].get("date") if rows else "-")

    try:
        total = await iter_speeches_by_range(from_date, until_date, save_batch,
                                             max_records=max_records)
        elapsed = time.time() - start
        status = db.corpus_status(conn)
        logger.info("done: fetched=%d newly_inserted=%d elapsed=%.1fs", total,
                     stats["inserted"], elapsed)
        logger.info("corpus now: %d speeches (%s 〜 %s)", status["speech_count"],
                     status["date_from"], status["date_until"])
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="国会会議録コーパスの取り込み")
    parser.add_argument("--from", dest="from_date", required=True,
                        help="取得開始日 YYYY-MM-DD")
    parser.add_argument("--until", dest="until_date", required=True,
                        help="取得終了日 YYYY-MM-DD")
    parser.add_argument("--max", dest="max_records", type=int, default=None,
                        help="取得件数の上限（テスト用）")
    args = parser.parse_args()
    asyncio.run(run(args.from_date, args.until_date, args.max_records))


if __name__ == "__main__":
    main()
