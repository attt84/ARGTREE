"""国会会議録検索APIクライアント（httpx・非同期・ページネーション対応）。

- ライブ検索: キーワード群を並列取得し、speechIDで重複排除
- 一括取り込み: 日付範囲を startRecord でページングしながら全件取得
"""
import asyncio
import logging

import httpx

from .config import get_settings
from .errors import ExternalAPIError

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "ARGTREE/1.0 (research tool; github.com/attt84/ARGTREE)"}

# APIレスポンスのフィールド名 → speeches テーブルのカラム名
FIELD_MAP = {
    "speechID": "speech_id",
    "issueID": "issue_id",
    "session": "session",
    "nameOfHouse": "house",
    "nameOfMeeting": "meeting",
    "issue": "issue",
    "date": "date",
    "speechOrder": "speech_order",
    "speaker": "speaker",
    "speakerYomi": "speaker_yomi",
    "speakerGroup": "speaker_group",
    "speakerPosition": "speaker_position",
    "speakerRole": "speaker_role",
    "speech": "speech",
    "speechURL": "speech_url",
    "meetingURL": "meeting_url",
}


def normalize_record(record: dict) -> dict:
    return {col: record.get(api_field) for api_field, col in FIELD_MAP.items()}


async def _fetch_page(client: httpx.AsyncClient, params: dict) -> dict:
    settings = get_settings()
    try:
        response = await client.get(settings.kokkai_api_url, params=params,
                                    headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.error("Kokkai API request failed: %s", e)
        raise ExternalAPIError("国会会議録検索APIとの通信に失敗しました") from e
    if "message" in data and "speechRecord" not in data:
        # APIはパラメータエラー等を message フィールドで返す
        logger.error("Kokkai API error response: %s", data.get("message"))
        raise ExternalAPIError("国会会議録検索APIがエラーを返しました")
    return data


async def search_speeches(queries: list[str], per_query: int = 15) -> list[dict]:
    """キーワード群で発言を並列検索し、正規化してspeechIDで重複排除して返す。"""
    async with httpx.AsyncClient() as client:
        tasks = [
            _fetch_page(client, {
                "any": q,
                "maximumRecords": min(per_query, 100),
                "recordPacking": "json",
            })
            for q in queries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    speeches: dict[str, dict] = {}
    ok_count = 0
    for q, result in zip(queries, results):
        if isinstance(result, BaseException):
            logger.warning("query '%s' failed: %s", q, result)
            continue
        ok_count += 1
        for record in result.get("speechRecord", []):
            row = normalize_record(record)
            if row["speech_id"] and row["speech_id"] not in speeches:
                speeches[row["speech_id"]] = row
    if ok_count == 0:
        raise ExternalAPIError("国会会議録検索APIとの通信に失敗しました")
    return list(speeches.values())


async def iter_speeches_by_range(from_date: str, until_date: str,
                                 batch_callback, max_records: int | None = None) -> int:
    """日付範囲の全発言をページングで取得し、100件ごとに batch_callback(rows) を呼ぶ。

    戻り値は取得した総件数。callbackで逐次保存することで中断・再開に耐える。
    """
    settings = get_settings()
    total_fetched = 0
    start_record = 1
    async with httpx.AsyncClient() as client:
        while True:
            data = await _fetch_page(client, {
                "from": from_date,
                "until": until_date,
                "maximumRecords": 100,
                "startRecord": start_record,
                "recordPacking": "json",
            })
            records = data.get("speechRecord", [])
            if not records:
                break
            rows = [normalize_record(r) for r in records]
            batch_callback(rows)
            total_fetched += len(rows)
            if max_records and total_fetched >= max_records:
                break
            next_position = data.get("nextRecordPosition")
            if not next_position:
                break
            start_record = next_position
            await asyncio.sleep(settings.kokkai_throttle_seconds)
    return total_fetched


def format_context(speeches: list[dict], char_limit: int | None = None) -> str:
    """発言リストをLLMプロンプト注入用のテキストに整形する。"""
    if char_limit is None:
        char_limit = get_settings().context_char_limit
    parts = []
    total = 0
    for s in speeches:
        block = (
            f"\n--- {s.get('meeting') or '不明な会議'} ({s.get('date') or ''}) ---\n"
            f"URL: {s.get('speech_url') or ''}\n"
            f"[{s.get('speaker') or '不明'}]: {s.get('speech') or ''}\n"
        )
        if total + len(block) > char_limit:
            break
        parts.append(block)
        total += len(block)
    return "".join(parts)
