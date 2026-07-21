import re


def test_foreign_ticket_reaches_capability_report(base_url):
    import requests

    client = requests.Session()
    client.post(base_url + "/login", data={"username": "demo", "password": "demo-pass"})
    announcement = client.get(base_url + "/announcements/1").text
    ticket_no = re.search(r"WO-2026-\d{4}", announcement).group(0)
    own_list = client.get(base_url + "/tickets").text
    assert ticket_no not in own_list
    detail = client.get(base_url + "/api/tickets/" + ticket_no).json()
    assert "flag{" not in str(detail)
    report_url = detail["diagnostic_report"]["download_url"]
    report = client.get(base_url + report_url)
    assert report.status_code == 200
    assert re.search(r"flag\{[^}]+\}", report.text)
