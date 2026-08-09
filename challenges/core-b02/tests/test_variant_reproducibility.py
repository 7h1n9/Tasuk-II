import requests


def test_variant_data_remains_stable_on_normal_reset(base_url, reset_instance):
    before = requests.post(base_url + "/api/warranty/check", json={"asset_no": "PC-2026-013", "department": "OPS"}).json()
    reset_instance()
    after = requests.post(base_url + "/api/warranty/check", json={"asset_no": "PC-2026-013", "department": "OPS"}).json()
    assert before["matched"] is after["matched"] is True
