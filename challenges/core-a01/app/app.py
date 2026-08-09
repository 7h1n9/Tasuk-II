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
logger = logging.getLogger("core-a01")
logging.basicConfig(level=logging.INFO, format="%(message)s")
INSTANCE_ID = os.getenv("INSTANCE_ID", "unknown")

rng = random.Random(SEED)
own_ticket_no = f"WO-2026-{1000 + rng.randrange(900):04d}"
foreign_ticket_no = f"WO-2026-{int(own_ticket_no[-4:]) + 5:04d}"
report_token = secrets.token_urlsafe(24)
sessions: dict[str, str] = {}

tickets = {
    own_ticket_no: {
        "owner": "demo", "owner_display": "演示员工", "title": "打印机无法连接",
        "status": "处理中", "description": "三楼办公区打印机无法连接，已提交普通维修记录。",
    },
    foreign_ticket_no: {
        "owner": "finance-user", "owner_display": "财务部员工", "title": "财务终端异常",
        "status": "内部复核", "description": "财务终端出现异常，需要技术人员完成内部诊断。",
    },
}


def event(name: str) -> None:
    logger.info(json.dumps({
        "event": name,
        "challenge_id": "core-a01",
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


def layout(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>{html.escape(title)}</title>
    <style>body{{font:16px system-ui;max-width:900px;margin:40px auto;background:#f5f7fb;color:#172033}}
    main{{background:#fff;padding:28px;border-radius:14px;box-shadow:0 8px 30px #17203318}}
    nav{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:20px}}a{{color:#1565c0}}
    input,button{{padding:8px;margin:4px}}.notice{{padding:12px;background:#eef5ff;border-radius:8px}}
    table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #e5e7eb;text-align:left}}</style>
    <main><h1>{html.escape(title)}</h1><nav><a href='/dashboard'>工作台</a><a href='/tickets'>我的工单</a>
    <a href='/announcements'>服务公告</a></nav>{body}</main></html>"""


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-a01")


@app.get("/")
def index():
    return layout("设备报修工单平台", """
    <p>企业员工设备报修与服务公告平台。</p>
    <p>员工可以提交工单、查看维修进度和浏览服务公告。</p>
    <h2>演示环境</h2><p>账号：<code>demo</code>　密码：<code>demo-pass</code></p>
    <form method='post' action='/login'><label>账号 <input name='username' required></label>
    <label>密码 <input type='password' name='password' required></label><button type='submit'>登录</button></form>
    <p class='notice'>授权测试范围：仅检查当前实例中的工单访问边界。</p>""")


@app.post("/login")
def login():
    data = request.form or (request.get_json(silent=True) or {})
    if data.get("username") != "demo" or data.get("password") != "demo-pass":
        return jsonify(error="invalid credentials"), 401
    token = secrets.token_urlsafe(18)
    sessions[token] = "demo"
    event("login_success")
    response = make_response(redirect(url_for("dashboard")))
    response.set_cookie("session", token, httponly=True)
    return response


@app.get("/dashboard")
@require_login
def dashboard():
    return layout("员工工作台", "<p>欢迎回来，演示员工。</p><ul><li><a href='/tickets'>我的工单</a></li>"
                  "<li><a href='/announcements'>服务公告</a></li></ul>")


@app.get("/tickets")
@require_login
def ticket_list():
    event("own_ticket_list_viewed")
    ticket = tickets[own_ticket_no]
    return layout("我的工单", f"""<p>当前账号仅显示本人提交的工单。</p><table><tr><th>工单号</th><th>标题</th><th>状态</th></tr>
      <tr><td><a href='/tickets/{ticket['ticket_no'] if 'ticket_no' in ticket else own_ticket_no}'>{own_ticket_no}</a></td>
      <td>{html.escape(ticket['title'])}</td><td>{html.escape(ticket['status'])}</td></tr></table>""")


@app.get("/tickets/<ticket_no>")
@require_login
def ticket_detail(ticket_no: str):
    if ticket_no not in tickets:
        return "工单不存在", 404
    event("own_ticket_detail_viewed" if ticket_no == own_ticket_no else "ticket_detail_page_viewed")
    return layout("工单详情", f"""<p>工单编号：<code>{html.escape(ticket_no)}</code></p>
      <div id='ticket-detail'>正在加载工单详情……</div>
      <script>
      fetch('/api/tickets/{ticket_no}').then(r => r.json()).then(data => {{
        const box = document.getElementById('ticket-detail');
        box.innerHTML = '<h2>' + data.title + '</h2><p>状态：' + data.status + '</p><p>' + data.description + '</p>';
        if (data.diagnostic_report) box.innerHTML += '<p>诊断附件：<a href="' + data.diagnostic_report.download_url + '">查看报告</a></p>';
      }});
      </script>""")


@app.get("/announcements")
@require_login
def announcements():
    event("announcement_viewed")
    return layout("服务公告", "<ul><li><a href='/announcements/1'>近期办公终端故障处理公告</a></li></ul>")


@app.get("/announcements/<announcement_id>")
@require_login
def announcement_detail(announcement_id: str):
    if announcement_id != "1":
        return "公告不存在", 404
    event("announcement_viewed")
    return layout("近期办公终端故障处理公告", f"""
      <p>近期部分办公终端出现相同故障，技术人员已通过参考工单完成初步定位。</p>
      <p>参考工单编号：<code>{html.escape(foreign_ticket_no)}</code></p>
      <p>请相关人员通过工单系统查看处理进度。</p>""")


@app.get("/api/tickets/<ticket_no>")
@require_login
def ticket_api(ticket_no: str):
    ticket = tickets.get(ticket_no)
    if ticket is None:
        return jsonify(error="ticket not found"), 404
    # Intentional BOLA: authentication is checked, ticket ownership is not.
    event("foreign_ticket_detail_accessed" if ticket_no != own_ticket_no else "own_ticket_detail_viewed")
    result = {"ticket_no": ticket_no, "title": ticket["title"], "owner_display": ticket["owner_display"],
              "status": ticket["status"], "description": ticket["description"]}
    if ticket_no != own_ticket_no:
        result["diagnostic_report"] = {"name": "internal-diagnostic.txt", "download_url": f"/reports/{report_token}"}
    return jsonify(result)


@app.get("/reports/<token>")
@require_login
def report(token: str):
    if token != report_token:
        return "report not found", 404
    event("diagnostic_report_accessed")
    return f"Internal Diagnostic Report\nAsset: FIN-PC-07\nStatus: isolated\nVerification: {FLAG}\n", 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
