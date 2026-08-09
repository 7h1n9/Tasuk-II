from __future__ import annotations

import base64
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
logger = logging.getLogger("core-a03")
logging.basicConfig(level=logging.INFO, format="%(message)s")

rng = random.Random(SEED)
project_code = f"PRJ-2026-{rng.randrange(1000, 9000):04d}"
archive_token = secrets.token_urlsafe(20)
sessions: dict[str, dict[str, str]] = {}


def event(name: str) -> None:
    logger.info(json.dumps({
        "event": name,
        "challenge_id": "core-a03",
        "instance_id": INSTANCE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False))


def encode_state(state: dict[str, str]) -> str:
    raw = json.dumps(state, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_state(value: str) -> dict[str, str]:
    if not value:
        return {}
    try:
        padded = value + "=" * (-len(value) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded).decode())
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError, UnicodeDecodeError):
        return {}


def current_session() -> dict[str, str] | None:
    return sessions.get(request.cookies.get("session", ""))


def portal_state() -> dict[str, str]:
    return decode_state(request.cookies.get("portal_state", ""))


def effective_role() -> str:
    state = portal_state()
    if state.get("workspace") == "leadership" and state.get("persona") == "admin":
        return "admin"
    session = current_session() or {}
    return session.get("role", "employee")


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_session() is None:
            if request.path.startswith("/api/") or request.path.startswith("/internal/"):
                return jsonify(error="authentication required"), 401
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


def page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>{html.escape(title)}</title>
    <style>body{{font:16px system-ui;max-width:960px;margin:38px auto;background:#f4f7fb;color:#172033}}
    main{{background:#fff;padding:28px;border-radius:15px;box-shadow:0 8px 28px #17203318}}
    nav{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:22px}}a{{color:#145db5}}
    input,select,button{{padding:9px;margin:4px;border:1px solid #bdc8d8;border-radius:7px;font:inherit}}
    button{{background:#145db5;color:#fff}}.notice{{padding:13px;background:#eef5ff;border-radius:9px}}
    code{{background:#f0f2f5;padding:2px 5px;border-radius:4px}}</style>
    <main><h1>{html.escape(title)}</h1><nav><a href='/projects'>项目中心</a>
    <a href='/approvals'>审批中心</a><a href='/settings'>个人设置</a><a href='/help'>使用说明</a></nav>{body}</main></html>"""


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-a03")


@app.get("/")
def index():
    return page("企业内部项目审批门户", """
      <p>项目成员可以查看项目、提交申请和跟踪审批状态。</p>
      <div class='notice'><strong>演示账号</strong>：<code>employee</code> / <code>employee-pass</code><br>
      当前账号是普通员工，页面会展示其可用的项目和审批功能。</div>
      <form method='post' action='/login'><label>账号 <input name='username' required></label>
      <label>密码 <input type='password' name='password' required></label><button>登录</button></form>
      <p>授权测试范围：仅检查当前门户实例中的登录状态和业务角色边界。</p>""")


@app.post("/login")
def login():
    data = request.form or (request.get_json(silent=True) or {})
    if data.get("username") != "employee" or data.get("password") != "employee-pass":
        return jsonify(error="invalid credentials"), 401
    token = secrets.token_urlsafe(18)
    sessions[token] = {"user": "employee", "role": "employee"}
    event("login_success")
    response = make_response(redirect(url_for("projects")))
    response.set_cookie("session", token, httponly=True, samesite="Lax")
    response.set_cookie("portal_state", encode_state({
        "user": "employee", "workspace": "engineering", "persona": "employee", "revision": "1",
    }), samesite="Lax")
    return response


@app.get("/help")
@require_login
def help_page():
    return page("门户使用说明", """
      <p>项目中心用于查看当前成员参与的项目，审批中心用于提交和跟踪申请。</p>
      <p>个人设置可以切换当前工作空间。切换后请观察浏览器保存的门户状态以及后续审批请求。</p>
      <p>管理员归档内容不会出现在普通项目列表中。</p>""")


@app.get("/projects")
@require_login
def projects():
    event("project_center_viewed")
    return page("项目中心", f"""
      <p>当前工作空间：研发项目组。</p><ul>
      <li><a href='/projects/{html.escape(project_code)}'>{html.escape(project_code)}</a> - 内部审批门户改造</li>
      </ul><p>项目成员可以从项目页进入申请和审批中心。</p>""")


@app.get("/projects/<project_id>")
@require_login
def project_detail(project_id: str):
    if project_id != project_code:
        return "项目不存在", 404
    return page("项目详情", f"""<p>项目编号：<code>{html.escape(project_code)}</code></p>
      <p>项目负责人正在收集门户改造申请。</p><p><a href='/approvals'>查看我的审批申请</a></p>""")


@app.get("/approvals")
@require_login
def approvals():
    event("approval_center_viewed")
    return page("审批中心", """
      <p>普通员工可以提交申请并查看自己的审批状态。</p>
      <form method='post' action='/approvals/request'><input name='title' value='门户改造建议'>
      <button>提交申请</button></form><p><a href='/api/approvals/queue'>查看当前审批队列状态</a></p>""")


@app.post("/approvals/request")
@require_login
def submit_request():
    title = str(request.form.get("title", "门户改造建议"))[:80]
    return page("申请已提交", f"<p>申请“{html.escape(title)}”已进入待审批状态。</p><p><a href='/approvals'>返回审批中心</a></p>")


@app.get("/settings")
@require_login
def settings():
    state = portal_state()
    return page("个人设置", f"""
      <p>当前用户：employee</p><p>当前工作空间：<code>{html.escape(state.get('workspace', 'engineering'))}</code></p>
      <form method='post' action='/settings/workspace'><label>工作空间
      <select name='workspace'><option value='engineering'>研发项目组</option>
      <option value='leadership'>管理协作区</option></select></label><button>保存工作空间</button></form>
      <p>工作空间用于加载对应的门户界面和审批导航。</p>""")


@app.post("/settings/workspace")
@require_login
def change_workspace():
    data = request.form or (request.get_json(silent=True) or {})
    workspace = str(data.get("workspace", "engineering"))
    if workspace not in {"engineering", "leadership"}:
        return jsonify(error="unsupported workspace"), 400
    state = {"user": "employee", "workspace": workspace, "persona": "employee", "revision": "2"}
    event("workspace_changed")
    response = make_response(redirect(url_for("settings")))
    response.set_cookie("portal_state", encode_state(state), samesite="Lax")
    return response


@app.get("/api/approvals/queue")
@require_login
def approval_queue():
    role = effective_role()
    event("approval_queue_viewed")
    if role == "admin":
        return jsonify(role="admin", items=["pending-budget-review"], admin_review_available=True)
    return jsonify(role="employee", items=["my-portal-change-request"], admin_review_available=False)


@app.get("/admin/reviews")
@require_login
def admin_reviews():
    if effective_role() != "admin":
        return jsonify(error="reviewer role required"), 403
    event("privileged_review_page_viewed")
    return page("管理审批审阅", f"""
      <p>当前审阅上下文：管理协作区。</p><p>内部项目归档：
      <a href='/internal/archive/{html.escape(archive_token)}'>下载项目归档</a></p>""")


@app.get("/internal/archive/<token>")
@require_login
def internal_archive(token: str):
    if token != archive_token or effective_role() != "admin":
        return "archive not found", 404
    event("internal_archive_downloaded")
    return f"Internal Project Archive\nProject: {project_code}\nRelease note: {FLAG}\n", 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
