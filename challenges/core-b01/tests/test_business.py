import requests


def test_public_business_entry(base_url):
    response = requests.get(base_url + "/")
    assert response.status_code == 200
    assert "内部物资检索平台" in response.text
    assert "物资检索" in response.text


def test_baseline_search(base_url):
    response = requests.get(base_url + "/search", params={"q": "终端", "format": "json"})
    assert response.status_code == 200
    assert response.json()["count"] == 1
