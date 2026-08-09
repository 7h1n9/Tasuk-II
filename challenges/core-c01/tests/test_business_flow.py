import requests


def test_business_pages(base_url):
    assert requests.get(base_url + "/").status_code == 200
    documents = requests.get(base_url + "/documents")
    assert documents.status_code == 200
    assert "办公设备使用指南" in documents.text
    assert requests.get(base_url + "/migration-notes").status_code == 200
