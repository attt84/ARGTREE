import requests
try:
    res = requests.post("http://localhost:8000/api/node_detail", json={
        "query": "消費税",
        "node_label": "税負担の公平性"
    })
    print(res.status_code)
    print(res.json())
except Exception as e:
    print(e)
