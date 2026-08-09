from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, session


app = Flask(__name__)
SEED = os.getenv("VARIANT_SEED", "demo")
FLAG = os.getenv("INSTANCE_FLAG", "flag{missing}")
INSTANCE_ID = os.getenv("INSTANCE_ID", "unknown")
SAMPLE_ASSET = "PC-2026-013"
SAMPLE_DEPARTMENT = "OPS"
INVALID_ASSET = "PC-0000-000"
INVALID_DEPARTMENT = "NONE"
DATA_DIR = Path("/app/data")
DB_PATH = DATA_DIR / "warranty.sqlite3"
logger = logging.getLogger("core-b02")
logging.basicConfig(level=logging.INFO, format="%(message)s")

query_count = 0
seen_valid_baseline = False
seen_invalid_baseline = False


def event(name: str) -> None:
    logger.info(json.dumps({
        "event": name,
        "challenge_id": "core-b02",
        "instance_id": INSTANCE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False))


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS assets (
                asset_no TEXT PRIMARY KEY,
                department TEXT NOT NULL,
                model TEXT NOT NULL,
                warranty_status TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS departments (
                code TEXT PRIMARY KEY,
                display_name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS service_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS query_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_matched INTEGER NOT NULL,
                request_kind TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        if connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0:
            assets = [(SAMPLE_ASSET, SAMPLE_DEPARTMENT, "ThinkCentre M90", "active", "2027-01-31")]
            departments = [("OPS", "运营支持"), ("HR", "人力资源"), ("FIN", "财务"), ("IT", "信息技术")]
            for index in range(1, 15):
                department = rng.choice(["OPS", "HR", "FIN", "IT"])
                asset_no = f"PC-2026-{100 + index:03d}"
                assets.append((asset_no, department, rng.choice(["ThinkCentre M90", "Latitude 5440", "ProBook 450"]), "active", f"2026-{rng.randint(8, 12):02d}-28"))
            connection.executemany("INSERT INTO assets VALUES (?, ?, ?, ?, ?)", assets)
            connection.executemany("INSERT INTO departments VALUES (?, ?)", departments)
            setting_key = f"warranty_marker_{rng.randrange(1000, 9999)}"
            connection.executemany(
                "INSERT INTO service_settings VALUES (?, ?)",
                [("retention_days", "180"), ("default_region", "east"), (setting_key, FLAG)],
            )
        else:
            connection.execute(
                "UPDATE service_settings SET setting_value = ? WHERE setting_value LIKE 'flag{%'",
                (FLAG,),
            )


initialize_database()
app.secret_key = hashlib.sha256((SEED + ":warranty-session").encode()).digest()


def page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'>
    <title>{html.escape(title)}</title>
    <style>
      body {{ max-width: 960px; margin: 36px auto; padding: 0 18px; font: 16px system-ui; color: #182233; background: #f4f7fb; }}
      main {{ background: white; border-radius: 16px; padding: 28px; box-shadow: 0 8px 28px #1e293b18; }}
      nav {{ display:flex; gap:18px; margin-bottom:24px; flex-wrap:wrap; }} a {{ color:#145db5; }}
      label {{ display:block; margin:12px 0 4px; }} input,button {{ padding:9px 11px; border:1px solid #b9c5d6; border-radius:8px; font:inherit; }}
      button {{ background:#145db5; color:white; cursor:pointer; }} .panel {{ padding:16px; background:#eef5ff; border-radius:10px; margin:14px 0; }}
      code {{ background:#f0f2f5; padding:2px 5px; border-radius:4px; }}
    </style><main><h1>{html.escape(title)}</h1>
    <nav><a href='/'>核验首页</a><a href='/help'>查询帮助</a><a href='/history'>最近记录</a></nav>{body}</main></html>"""


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-b02")


@app.get("/")
def index():
    return page("资产保修核验平台", """
      <p>员工可以输入设备编号和所属部门，确认设备是否仍处于内部保修范围。</p>
      <div class='panel'><strong>授权测试范围</strong><br>仅检查当前实例中的保修核验功能。</div>
      <form id='warranty-form'>
        <label for='asset_no'>设备编号</label><input id='asset_no' name='asset_no' required>
        <label for='department'>部门代码</label><input id='department' name='department' required>
        <button type='submit'>开始核验</button>
      </form>
      <section class='panel'><h2>示例查询</h2>
        <p>有效示例：<code data-asset-no='PC-2026-013' data-department='OPS'>PC-2026-013 / OPS</code></p>
        <p>无效示例：<code data-asset-no='PC-0000-000' data-department='NONE'>PC-0000-000 / NONE</code></p>
      </section>
      <p id='result' aria-live='polite'>查询结果将在这里显示。</p>
      <script>
        const QUERY_ENDPOINT = '/api/warranty/check';
        const FIELD_NAMES = ['asset_no', 'department'];
        const form = document.getElementById('warranty-form');
        form.addEventListener('submit', async (event) => {
          event.preventDefault();
          const payload = Object.fromEntries(new FormData(form).entries());
          const response = await fetch(QUERY_ENDPOINT, {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
          });
          const data = await response.json();
          document.getElementById('result').textContent = data.message || '查询失败';
        });
      </script>""")


@app.get("/help")
def help_page():
    return page("查询帮助", """
      <p><strong>设备编号</strong>用于定位资产，<strong>部门代码</strong>用于确认资产归属。</p>
      <p>页面只展示是否存在符合条件的保修记录，不展示底层记录内容。</p>
      <p>建议先分别执行首页中的有效和无效示例，再从浏览器网络面板观察核验请求。</p>
      <p>平台使用轻量关系型存储，验证接口只返回稳定的真假结果。</p>
    """)


@app.get("/history")
def history():
    rows = session.get("history", [])[-8:]
    items = "".join(f"<li>{html.escape(row['message'])}</li>" for row in reversed(rows)) or "<li>当前会话还没有核验记录。</li>"
    return page("最近核验记录", f"<p>这里只显示当前会话的最近结果。</p><ul>{items}</ul>")


def _request_kind(asset_no: str, department: str) -> str:
    if asset_no == SAMPLE_ASSET and department == SAMPLE_DEPARTMENT:
        return "valid_baseline"
    if asset_no == INVALID_ASSET and department == INVALID_DEPARTMENT:
        return "invalid_baseline"
    return "probe"


def _log_probe_events(department: str, matched: bool, kind: str) -> None:
    lower = department.lower()
    if kind == "probe":
        event("structured_probe_observed")
        event("boolean_true_probe" if matched else "boolean_false_probe")
    if "sqlite_master" in lower or "pragma_table_info" in lower:
        event("schema_reference_observed")
    if "setting" in lower or "flag" in lower:
        event("sensitive_record_probe")


@app.post("/api/warranty/check")
def warranty_check():
    global query_count, seen_valid_baseline, seen_invalid_baseline
    query_count += 1
    payload = request.get_json(silent=True) or {}
    asset_no = str(payload.get("asset_no", ""))[:256]
    department = str(payload.get("department", ""))[:1024]
    kind = _request_kind(asset_no, department)
    matched = False
    try:
        # The asset number is correctly parameterized. The department is the
        # single legacy compatibility input that is interpolated into this query.
        query = """
            SELECT 1 FROM assets
            WHERE asset_no = ?
            AND department = '%s'
            LIMIT 1
        """ % department
        with connect() as connection:
            matched = connection.execute(query, (asset_no,)).fetchone() is not None
            connection.execute(
                "INSERT INTO query_audit(result_matched, request_kind, created_at) VALUES (?, ?, ?)",
                (int(matched), kind, datetime.now(timezone.utc).isoformat()),
            )
    except Exception:  # noqa: BLE001 - all query failures become an ordinary false result
        matched = False

    if kind == "valid_baseline" and not seen_valid_baseline:
        seen_valid_baseline = True
        event("valid_baseline_observed")
    elif kind == "invalid_baseline" and not seen_invalid_baseline:
        seen_invalid_baseline = True
        event("invalid_baseline_observed")
    _log_probe_events(department, matched, kind)
    message = "存在符合条件的保修记录" if matched else "未找到符合条件的保修记录"
    session.setdefault("history", []).append({"matched": matched, "message": message})
    session["history"] = session["history"][-8:]
    return jsonify(matched=matched, message=message)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
