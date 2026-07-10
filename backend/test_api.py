import requests

SPEECH_API_URL = "https://kokkai.ndl.go.jp/api/speech"
params = {
    "any": "消費税",
    "maximumRecords": 10,
    "recordPacking": "json"
}
headers = {
    "User-Agent": "Mozilla/5.0"
}
response = requests.get(SPEECH_API_URL, params=params, headers=headers)
data = response.json()
print("Total records:", data.get("numberOfRecords"))
for speech in data.get("speechRecord", []):
    print(f"[{speech.get('speaker')}] {len(speech.get('speech', ''))} chars")
    # print(speech.get('speech', '')[:50])
