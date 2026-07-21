import re

import requests


def test_report_capability_changes_after_reset(base_url, reset_instance):
    client = requests.Session()
    client.post(base_url + "/login", data={"username": "demo", "password": "demo-pass"})
    ticket_no = re.search(r"WO-2026-\d{4}", client.get(base_url + "/announcements/1").text).group(0)
    old_report = client.get(base_url + "/api/tickets/" + ticket_no).json()["diagnostic_report"]["download_url"]
    reset_instance()
    client.post(base_url + "/login", data={"username": "demo", "password": "demo-pass"})
    new_report = client.get(base_url + "/api/tickets/" + ticket_no).json()["diagnostic_report"]["download_url"]
    assert old_report != new_report
    assert client.get(base_url + old_report).status_code == 404
