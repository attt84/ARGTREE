import requests
try:
    res = requests.post("http://localhost:8000/api/search", json={
        "query": "少子化対策",
        "use_super_search": True
    })
    print(res.status_code)
    tree = res.json().get('tree', {})
    print("Nodes:", len(tree.get('nodes', [])))
    print("Edges:", len(tree.get('edges', [])))
except Exception as e:
    print(e)
