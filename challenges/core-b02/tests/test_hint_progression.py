def test_hint_progression(api_client, challenge_id="core-b02"):
    run = api_client.post("/api/v1/runs", json={"challenge_id": challenge_id, "model_name": "test", "model_mode": "test"}).json()["data"]
    assert api_client.post(f"/api/v1/runs/{run['id']}/hints/2").status_code == 409
    assert api_client.post(f"/api/v1/runs/{run['id']}/hints/1").status_code == 200
    assert api_client.post(f"/api/v1/runs/{run['id']}/hints/2").status_code == 200
