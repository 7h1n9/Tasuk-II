import requests


def test_business_pages_and_examples(base_url):
    home = requests.get(base_url + "/")
    assert home.status_code == 200
    assert "/help" in home.text and "/history" in home.text
    assert "PC-2026-013" in home.text and "PC-0000-000" in home.text
    assert requests.get(base_url + "/help").status_code == 200
    assert requests.get(base_url + "/history").status_code == 200


def test_true_and_false_baselines(base_url):
    valid = requests.post(base_url + "/api/warranty/check", json={"asset_no": "PC-2026-013", "department": "OPS"})
    invalid = requests.post(base_url + "/api/warranty/check", json={"asset_no": "PC-0000-000", "department": "NONE"})
    assert valid.status_code == invalid.status_code == 200
    assert valid.json()["matched"] is True
    assert invalid.json()["matched"] is False
