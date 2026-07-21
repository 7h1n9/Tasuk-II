import os
import requests


def test_public_business_entry(base_url):
    response = requests.get(base_url + "/")
    assert response.status_code == 200
    assert "客户资料协作平台" in response.text
    assert "协作任务" in response.text


def test_login_and_own_profile(base_url):
    client = requests.Session()
    client.post(base_url + "/login", data={"username": "demo", "password": "demo-pass"})
    response = client.get(base_url + "/profiles/customer-demo")
    assert response.status_code == 200
    assert response.json()["id"] == "customer-demo"
