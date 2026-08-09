import re
import requests


def test_public_pages_hide_private_content(base_url):
    for path in ("/", "/documents", "/migration-notes"):
        body = requests.get(base_url + path).text.lower()
        assert not re.search(r"flag\\{", body, re.I)
        assert "double decode" not in body
        assert "path traversal" not in body
    assert requests.get(base_url + "/preview?path=/etc/passwd").status_code == 403
