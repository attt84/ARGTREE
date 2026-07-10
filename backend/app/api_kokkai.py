import requests
import json
import logging

logger = logging.getLogger(__name__)

KOKKAI_API_URL = "https://kokkai.ndl.go.jp/api/speech"

def fetch_diet_minutes(query: str | list[str], max_records: int = 15) -> str:
    """
    国会会議録検索APIから指定されたキーワードを含む発言を直接取得する。
    クエリがリストの場合は並列または順次に取得し、マージして返す。
    """
    queries = query if isinstance(query, list) else [query]
    
    # 複数クエリの場合は1クエリあたりの取得件数を減らす（最大合計を維持）
    per_query_max = max(5, max_records // len(queries))
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    all_minutes_text = ""
    
    for q in queries:
        params = {
            "any": q,
            "maximumRecords": per_query_max,
            "recordPacking": "json"
        }
        
        try:
            response = requests.get(KOKKAI_API_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "speechRecord" in data:
                for speech in data["speechRecord"]:
                    meeting_name = speech.get("nameOfMeeting", "不明な会議")
                    date = speech.get("date", "")
                    speaker = speech.get("speaker", "不明")
                    speech_text = speech.get("speech", "")
                    speech_url = speech.get("speechURL", "")
                    
                    all_minutes_text += f"\n--- {meeting_name} ({date}) [クエリ: {q}] ---\n"
                    if speech_url:
                        all_minutes_text += f"URL: {speech_url}\n"
                    all_minutes_text += f"[{speaker}]: {speech_text}\n"
                    
        except Exception as e:
            logger.error(f"Error fetching Kokkai API for query '{q}': {e}")
            continue

    if not all_minutes_text.strip():
        return "関連する議事録が見つかりませんでした。"
        
    return all_minutes_text
