import requests
import json
import logging

logger = logging.getLogger(__name__)

KOKKAI_API_URL = "https://kokkai.ndl.go.jp/api/meeting"

def fetch_diet_minutes(query: str, max_records: int = 3) -> str:
    """
    国会会議録検索APIから指定されたキーワードに関連する議事録を取得する。
    """
    params = {
        "any": query,
        "maximumRecords": max_records,
        "recordPacking": "json"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(KOKKAI_API_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        minutes_text = ""
        if "meetingRecord" in data:
            for meeting in data["meetingRecord"]:
                meeting_name = meeting.get("nameOfMeeting", "不明な会議")
                date = meeting.get("date", "")
                minutes_text += f"\n--- 会議: {meeting_name} ({date}) ---\n"
                
                if "speechRecord" in meeting:
                    for speech in meeting["speechRecord"]:
                        speaker = speech.get("speaker", "不明")
                        speech_text = speech.get("speech", "")
                        minutes_text += f"[{speaker}]: {speech_text}\n"
        
        if not minutes_text.strip():
            return "関連する議事録が見つかりませんでした。"
            
        return minutes_text
        
    except Exception as e:
        logger.error(f"Error fetching Kokkai API: {e}")
        return f"議事録の取得中にエラーが発生しました: {str(e)}"
