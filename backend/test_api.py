import requests

KOKKAI_API_URL = "https://kokkai.ndl.go.jp/api/meeting"
params = {
    "any": "消費税",
    "maximumRecords": 3,
    "recordPacking": "json"
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
try:
    response = requests.get(KOKKAI_API_URL, params=params, headers=headers, timeout=10)
    print("Status:", response.status_code)
    print("Content:", response.text[:200])
except Exception as e:
    print("Error:", e)
