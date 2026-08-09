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
from jinja2 import Environment, StrictUndefined, UndefinedError, select_autoescape


app = Flask(__name__)
FLAG = os.getenv("INSTANCE_FLAG", "flag{missing}")
SEED = os.getenv("VARIANT_SEED", "demo")
INSTANCE_ID = os.getenv("INSTANCE_ID", "unknown")
logger = logging.getLogger("core-a04")
logging.basicConfig(level=logging.INFO, format="%(message)s")

rng = random.Random(SEED)
template_id = f"TPL-2026-{rng.randrange(1000, 9000):04d}"
employee_alias = f"林工-{rng.randrange(10, 99):02d}"
sessions: dict[str, str] = {}
templates: dict[str, dict[str, str]] = {
    template_id: {"name": "季度系统通知", "body": "各位同事，{{ employee_name }} 所在的 {{ department }} 将于 {{ date }} 发布通知。"}
}

# This is deliberately a real Jinja rendering context. The application object
# is an accidental server-side context exposure; the flag is not a template
# variable named `flag`.
APPLICATION = {"settings": {"notice_footer": FLAG, "product": "mail-preview"}}
environment = Environment(undefined=StrictUndefined, autoescape=select_autoescape(["html", "xml"]))


def event(name: str) -> None:
    logger.info(json.dumps({
        "event": name,
        "challenge_id": "core-a04",
        "instance_id": INSTANCE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False))


def current_user() -> str | None:
    return sessions.get(request.cookies.get("session", ""))


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/"):
                return jsonify(error="authentication required"), 401
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


def page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>{html.escape(title)}</title>
    <style>body{{font:16px system-ui;max-width:960px;margin:38px auto;background:#f4f7fb;color:#172033}}
    main{{background:#fff;padding:28px;border-radius:15px;box-shadow:0 8px 28px #17203318}}
    nav{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:22px}}a{{color:#145db5}}
    input,textarea,button{{padding:9px;margin:4px;border:1px solid #bdc8d8;border-radius:7px;font:inherit}}
    textarea{{width:95%;min-height:130px}}button{{background:#145db5;color:#fff}}
    .notice{{padding:13px;background:#eef5ff;border-radius:9px}}code{{background:#f0f2f5;padding:2px 5px;border-radius:4px}}
    </style><main><h1>{html.escape(title)}</h1><nav><a href='/templates'>模板中心</a>
    <a href='/templates/new'>创建模板</a><a href='/help'>变量说明</a><a href='/profile'>个人资料</a></nav>{body}</main></html>"""


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-a04")


@app.get("/")
def index():
    return page("企业邮件模板预览系统", """
      <p>企业员工可以创建通知模板、选择模板并预览发送效果。</p>
      <div class='notice'><strong>演示账号</strong>：<code>employee</code> / <code>employee-pass</code><br>
      模板支持变量说明页列出的员工姓名、部门和日期字段。</div>
      <form method='post' action='/login'><label>账号 <input name='username' required></label>
      <label>密码 <input type='password' name='password' required></label><button>登录</button></form>
      <p>授权测试范围：仅检查当前实例的模板预览处理逻辑。</p>""")


@app.post("/login")
def login():
    data = request.form or (request.get_json(silent=True) or {})
    if data.get("username") != "employee" or data.get("password") != "employee-pass":
        return jsonify(error="invalid credentials"), 401
    token = secrets.token_urlsafe(18)
    sessions[token] = "employee"
    event("login_success")
    response = make_response(redirect(url_for("templates_page")))
    response.set_cookie("session", token, httponly=True, samesite="Lax")
    return response


@app.get("/help")
@require_login
def help_page():
    return page("模板变量说明", """
      <p>普通模板可以使用以下变量：</p><ul><li><code>{{ employee_name }}</code>：员工姓名</li>
      <li><code>{{ department }}</code>：所属部门</li><li><code>{{ date }}</code>：预览日期</li></ul>
      <p>预览会按照模板语法实际渲染内容；无法识别的变量会显示处理错误。</p>""")


@app.get("/profile")
@require_login
def profile():
    return page("个人资料", f"<p>姓名：{html.escape(employee_alias)}</p><p>部门：产品运营部</p><p>通知模板权限：标准员工</p>")


@app.get("/templates")
@require_login
def templates_page():
    event("template_center_viewed")
    links = "".join(f"<li><a href='/templates/{html.escape(key)}'>{html.escape(value['name'])}</a></li>" for key, value in templates.items())
    return page("模板中心", f"<p>已保存的通知模板：</p><ul>{links}</ul><p><a href='/templates/new'>创建新的通知模板</a></p>")


@app.get("/templates/new")
@require_login
def new_template():
    return page("创建通知模板", """
      <form method='post' action='/api/templates'><label>模板名称 <input name='name' value='会议通知'></label>
      <label>模板正文</label><textarea name='body'>各位同事，{{ employee_name }} 的 {{ department }} 会议安排在 {{ date }}。</textarea>
      <button>保存模板</button></form><p>保存后可以在模板详情中预览。</p>""")


@app.post("/api/templates")
@require_login
def create_template():
    data = request.form or (request.get_json(silent=True) or {})
    name = str(data.get("name", "未命名模板"))[:80]
    body = str(data.get("body", ""))[:4000]
    if not body:
        return jsonify(error="template body required"), 400
    new_id = f"TPL-2026-{rng.randrange(1000, 9000):04d}"
    while new_id in templates:
        new_id = f"TPL-2026-{rng.randrange(1000, 9000):04d}"
    templates[new_id] = {"name": name, "body": body}
    event("template_created")
    if request.form:
        return redirect(url_for("template_detail", template_key=new_id))
    return jsonify(template_id=new_id)


@app.get("/templates/<template_key>")
@require_login
def template_detail(template_key: str):
    record = templates.get(template_key)
    if record is None:
        return "template not found", 404
    event("template_detail_viewed")
    return page("模板预览", f"""
      <p>模板编号：<code>{html.escape(template_key)}</code></p><p>名称：{html.escape(record['name'])}</p>
      <form method='post' action='/api/templates/{html.escape(template_key)}/preview'>
      <textarea name='body'>{html.escape(record['body'])}</textarea><button>预览模板</button></form>
      <p>如需了解变量含义，请查看<a href='/help'>变量说明</a>。</p>""")


def render_body(body: str) -> str:
    template = environment.from_string(body)
    return template.render(employee_name=employee_alias, department="产品运营部",
                           date="2026-08-09", application=APPLICATION)


@app.route("/api/templates/<template_key>/preview", methods=["POST"])
@require_login
def preview(template_key: str):
    record = templates.get(template_key)
    if record is None:
        return jsonify(error="template not found"), 404
    data = request.form or (request.get_json(silent=True) or {})
    body = str(data.get("body", record["body"]))[:4000]
    event("template_preview_requested")
    try:
        rendered = render_body(body)
    except UndefinedError as exc:
        event("template_context_error")
        return jsonify(error="template rendering failed", detail=str(exc),
                       available_roots=["employee_name", "department", "date", "application"]), 422
    return jsonify(template_id=template_key, rendered=rendered)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
