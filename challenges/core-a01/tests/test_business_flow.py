import re
import requests


def logged_in(base_url):
    client = requests.Session()
    response = client.post(base_url + "/login", data={"username": "demo", "password": "demo-pass"})
    assert response.status_code == 200
    return client


def test_business_pages_and_demo_login(base_url):
    client = logged_in(base_url)
    assert client.get(base_url + "/dashboard").status_code == 200
    tickets = client.get(base_url + "/tickets")
    assert tickets.status_code == 200
    own_ticket = re.search(r"WO-2026-\d{4}", tickets.text).group(0)
    assert client.get(base_url + "/tickets/" + own_ticket).status_code == 200
    announcement = client.get(base_url + "/announcements/1")
    assert announcement.status_code == 200
    assert "WO-2026-" in announcement.text


def test_unauthenticated_ticket_api_is_denied(base_url):
    assert requests.get(base_url + "/api/tickets/WO-2026-1000").status_code == 401
