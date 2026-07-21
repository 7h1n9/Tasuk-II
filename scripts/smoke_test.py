from __future__ import annotations

import sys
import time
from dataclasses import dataclass
import os

import httpx


BASE = os.environ.get("API_BASE_URL", "http://localhost:18080")


@dataclass
class SmokeResult:
    name: str
    ok: bool
    detail: str


def wait_for_backend(timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE}/health", timeout=5.0)
            if r.status_code == 200:
                return
        except Exception:
            time.sleep(2)
    raise RuntimeError("backend not ready")


def main() -> int:
    wait_for_backend()
    results: list[SmokeResult] = []
    try:
        r = httpx.get(f"{BASE}/api/v1/challenges", timeout=10.0)
        r.raise_for_status()
        challenges = r.json()["data"]["items"]
        results.append(SmokeResult("challenges", len(challenges) >= 8, f"count={len(challenges)}"))

        challenge_id = challenges[0]["id"]
        r = httpx.post(f"{BASE}/api/v1/instances", json={"challenge_id": challenge_id}, timeout=120.0)
        r.raise_for_status()
        inst = r.json()["data"]
        instance_id = inst["instance_id"]
        results.append(SmokeResult("instance-create", True, instance_id))

        r = httpx.get(f"{BASE}/api/v1/instances/{instance_id}", timeout=10.0)
        r.raise_for_status()
        instance_payload = r.json()["data"]
        results.append(SmokeResult("instance-get", instance_payload["status"] in {"running", "starting"}, instance_payload["status"]))

        r = httpx.post(f"{BASE}/api/v1/instances/{instance_id}/submit", json={"flag": "flag{wrong}"}, timeout=10.0)
        r.raise_for_status()
        submit_payload = r.json()["data"]
        results.append(SmokeResult("flag-wrong", not submit_payload["correct"], r.text))

        r = httpx.post(f"{BASE}/api/v1/instances/{instance_id}/reset", timeout=120.0)
        r.raise_for_status()
        results.append(SmokeResult("instance-reset", True, r.text))

        r = httpx.delete(f"{BASE}/api/v1/instances/{instance_id}", timeout=120.0)
        r.raise_for_status()
        results.append(SmokeResult("instance-destroy", True, r.text))
    except Exception as exc:  # noqa: BLE001
        print(exc)
        return 1

    for item in results:
        print(f"{item.name}: {'PASS' if item.ok else 'FAIL'} - {item.detail}")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
