import re
import requests


def test_public_pages_hide_schema_and_flag(base_url):
    for path in ("/", "/help", "/history"):
        body = requests.get(base_url + path).text.lower()
        assert "service_settings" not in body
        assert "flag{" not in body
    response = requests.post(base_url + "/api/warranty/check", json={"asset_no": "bad", "department": "'"})
    assert response.status_code == 200
    assert not re.search(r"sqlite|syntax error|traceback|flag\\{", response.text, re.I)
