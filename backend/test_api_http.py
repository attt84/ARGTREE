import requests
try:
    res = requests.post("http://localhost:8000/api/search", json={"query": "消費税"})
    print(res.status_code)
    print(res.json())
except Exception as e:
    print(e)
