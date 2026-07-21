import requests


def test_authorized_object_boundary_is_broken(base_url):
    client = requests.Session()
    client.post(base_url + "/login", data={"username": "demo", "password": "demo-pass"})
    own = client.get(base_url + "/profiles/customer-demo")
    foreign = client.get(base_url + "/profiles/customer-north")
    assert own.status_code == 200
    assert foreign.status_code == 200
    assert foreign.json().get("note", "").startswith("内部协作备注：flag{")
