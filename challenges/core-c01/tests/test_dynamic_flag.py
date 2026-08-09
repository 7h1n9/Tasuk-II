import re
import requests


def test_public_pages_do_not_contain_flag(base_url):
    response = requests.get(base_url + "/")
    assert not re.search(r"flag\{", response.text, re.I)
