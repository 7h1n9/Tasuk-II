from __future__ import annotations

import html
import json
import logging
import os
import random
import secrets
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, make_response, redirect, request, url_for


app = Flask(__name__)
FLAG = os.getenv("INSTANCE_FLAG", "flag{missing}")
SEED = os.getenv("VARIANT_SEED", "demo")
INSTANCE_ID = os.getenv("INSTANCE_ID", "unknown")
logger = logging.getLogger("core-b04")
logging.basicConfig(level=logging.INFO, format="%(message)s")

rng = random.Random(SEED)
own_event_a = f"EV-2026-{rng.randrange(1000, 9000):04d}"
own_event_b = f"EV-2026-{rng.randrange(1000, 9000):04d}"
admin_event = f"EV-2026-{rng.randrange(1000, 9000):04d}"
while len({own_event_a, own_event_b, admin_event}) != 3:
    admin_event = f"EV-2026-{rng.randrange(1000, 9000):04d}"
sessions: dict[str, str] = {}
report_tokens: dict[str, str] = {}

events = [
    {"event_id": own_event_a, "actor": "demo", "department": "engineering", "date": "2026-08-02",
     "action": "登录知识库", "risk": "low", "note": "员工正常登录记录", "scope": "personal"},
    {"event_id": own_event_b, "actor": "demo", "department": "engineering", "date": "2026-08-05",
     "action": "导出个人审计列表", "risk": "low", "note": "员工查看自己的审计记录", "scope": "personal"},
    {"event_id": admin_event, "actor": "audit-admin", "department": "security-ops", "date": "2026-08-06",
     "action": "查看高风险策略变更", "risk": "critical", "note": "内部管理员复核报告，含敏感处置结论", "scope": "internal"},
]


def event(name: str) -> None:
    logger.info(json.dumps({
        "event": name,
        "challenge_id": "core-b04",
        "instance_id": INSTANCE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False))


def current_user() -> str | None:
    return sessions.get(request.cookies.get("session", ""))


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/") or request.path.startswith("/reports/"):
                return jsonify(error="authentication required"), 401
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


def page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>{html.escape(title)}</title>
    <style>body{{font:16px system-ui;max-width:980px;margin:38px auto;background:#f4f7fb;color:#172033}}
    main{{background:#fff;padding:28px;border-radius:15px;box-shadow:0 8px 28px #17203318}}
    nav{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:22px}}a{{color:#145db5}}
    input,select,button{{padding:9px;margin:4px;border:1px solid #bdc8d8;border-radius:7px;font:inherit}}
    button{{background:#145db5;color:#fff}}table{{width:100%;border-collapse:collapse}}
    td,th{{padding:10px;border-bottom:1px solid #e6eaf0;text-align:left}}
    .notice{{padding:13px;background:#eef5ff;border-radius:9px}}code{{background:#f0f2f5;padding:2px 5px;border-radius:4px}}
    </style><main><h1>{html.escape(title)}</h1><nav><a href='/dashboard'>工作台</a>
    <a href='/audit'>审计查询</a><a href='/export'>报告导出</a><a href='/help'>使用说明</a></nav>{body}</main></html>"""


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-b04")


@app.get("/")
def index():
    return page("企业审计查询平台", """
      <p>安全审计人员可以查询操作日志、查看风险事件并导出审计报告。</p>
      <div class='notice'><strong>演示账号</strong>：<code>demo</code> / <code>demo-pass</code><br>
      普通用户登录后默认查看自己的审计记录。</div>
      <form method='post' action='/login'><label>账号 <input name='username' required></label>
      <label>密码 <input type='password' name='password' required></label><button>登录</button></form>
      <p>授权测试范围：仅检查当前审计平台实例的数据筛选和报告导出。</p>""")


@app.post("/login")
def login():
    data = request.form or (request.get_json(silent=True) or {})
    if data.get("username") != "demo" or data.get("password") != "demo-pass":
        return jsonify(error="invalid credentials"), 401
    token = secrets.token_urlsafe(18)
    sessions[token] = "demo"
    event("login_success")
    response = make_response(redirect(url_for("dashboard")))
    response.set_cookie("session", token, httponly=True, samesite="Lax")
    return response


@app.get("/dashboard")
@require_login
def dashboard():
    return page("审计工作台", """
      <p>欢迎进入企业安全审计工作台。</p><ul><li><a href='/audit'>查询操作日志</a></li>
      <li><a href='/export'>导出审计报告</a></li><li><a href='/help'>查看筛选说明</a></li></ul>""")


@app.get("/help")
@require_login
def help_page():
    return page("审计查询说明", """
      <p>查询支持日期范围和部门范围。默认范围是当前登录员工的个人记录。</p>
      <p>部门选项包括“我的部门”和“全部部门”，查询返回的记录需要结合 actor、department 和 scope 判断。</p>
      <p>报告导出页面可以根据查询结果中的事件编号生成审计报告。</p>""")


@app.get("/audit")
@require_login
def audit_page():
    event("audit_page_viewed")
    return page("审计查询", """
      <form id='query'><label>开始日期 <input name='from' value='2026-01-01'></label>
      <label>结束日期 <input name='to' value='2026-12-31'></label>
      <label>部门 <select name='department'><option value='engineering'>我的部门</option><option value='all'>全部部门</option></select></label>
      <button>查询</button></form><pre id='results'>查询结果将在这里显示。</pre>
      <script>document.getElementById('query').addEventListener('submit', async (e)=>{e.preventDefault();
      const p=new URLSearchParams(new FormData(e.target)); const r=await fetch('/api/audit/events?'+p); 
      document.getElementById('results').textContent=JSON.stringify(await r.json(),null,2);});</script>""")


def serialized(record: dict[str, str]) -> dict[str, str]:
    return {key: record[key] for key in ("event_id", "actor", "department", "date", "action", "risk", "note", "scope")}


@app.get("/api/audit/events")
@require_login
def audit_events():
    department = str(request.args.get("department", "engineering")).lower()
    date_from = str(request.args.get("from", "0000-00-00"))
    date_to = str(request.args.get("to", "9999-99-99"))
    event("audit_query")
    candidates = [record for record in events if date_from <= record["date"] <= date_to]
    if department == "engineering":
        visible = [record for record in candidates if record["actor"] == current_user() and record["department"] == department]
    elif department == "all":
        # Intentional broken filtering: the normal all-departments selector
        # expands the dataset but forgets to retain the current-user scope.
        visible = candidates
    else:
        visible = [record for record in candidates if record["department"] == department]
    if any(record["scope"] == "internal" for record in visible):
        event("sensitive_record_access")
    return jsonify(items=[serialized(record) for record in visible])


@app.get("/export")
@require_login
def export_page():
    return page("审计报告导出", """
      <p>从审计查询结果中复制事件编号，然后生成对应的审计报告。</p>
      <form method='post' action='/api/audit/export'><label>事件编号 <input name='event_id' required></label><button>生成报告</button></form>
      <p>导出接口会返回一次性报告下载地址。</p>""")


@app.post("/api/audit/export")
@require_login
def audit_export():
    data = request.form or (request.get_json(silent=True) or {})
    event_id = str(data.get("event_id", ""))
    record = next((item for item in events if item["event_id"] == event_id), None)
    if record is None:
        return jsonify(error="event not found"), 404
    event("audit_export")
    token = secrets.token_urlsafe(20)
    report_tokens[token] = event_id
    return jsonify(event_id=event_id, download_url=f"/reports/{token}")


@app.get("/reports/<token>")
@require_login
def report(token: str):
    event_id = report_tokens.get(token)
    if event_id is None:
        return "report not found", 404
    record = next((item for item in events if item["event_id"] == event_id), None)
    if record is None:
        return "report not found", 404
    disposition = FLAG if record["scope"] == "internal" else "No sensitive disposition"
    return f"Audit Report\nEvent: {event_id}\nRisk: {record['risk']}\nDisposition: {disposition}\n", 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
