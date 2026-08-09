import re
import requests


def test_normal_response_does_not_contain_flag(base_url):
    response = requests.post(base_url + "/api/warranty/check", json={"asset_no": "PC-2026-013", "department": "OPS"})
    assert not re.search(r"flag\{", response.text, re.I)
