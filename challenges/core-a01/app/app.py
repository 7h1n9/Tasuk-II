from __future__ import annotations

import os
import secrets
from html import escape
from urllib.parse import quote

from flask import Flask, jsonify, make_response, redirect, request, url_for

app = Flask(__name__)
FLAG = os.getenv("INSTANCE_FLAG", "flag{missing}")
users = {"demo": "demo-pass"}
sessions: dict[str, str] = {}
profiles = {
    "customer-demo": {"owner": "demo", "name": "演示客户", "industry": "制造业", "note": "公开客户资料"},
    "customer-north": {"owner": "north", "name": "北区重点客户", "industry": "能源服务", "note": "内部协作备注："},
}


def page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>{escape(title)}</title>
    <style>body{{font:16px system-ui;max-width:820px;margin:40px auto;background:#f5f7fb;color:#172033}}
    main{{background:white;padding:28px;border-radius:14px;box-shadow:0 8px 30px #17203318}}a{{color:#1565c0}}
    nav{{display:flex;gap:18px;margin-bottom:20px}}code{{background:#eef2f7;padding:2px 5px}}</style>
    <main><h1>{escape(title)}</h1><nav><a href='/'>首页</a><a href='/me'>我的资料</a><a href='/workspace'>协作任务</a><a href='/activity'>最近访问</a></nav>{body}</main></html>"""


def current_user() -> str | None:
    return sessions.get(request.cookies.get("session", ""))


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-a01")


@app.get("/")
def index():
    return page("客户资料协作平台", """
    <p>用于管理客户资料、协作任务和最近访问记录的演示系统。</p>
    <h2>演示环境</h2><p>账号：<code>demo</code>　密码：<code>demo-pass</code></p>
    <form method='post' action='/login'><label>账号 <input name='username' autocomplete='username' required></label>
    <label>密码 <input type='password' name='password' autocomplete='current-password' required></label>
    <button type='submit'>登录</button></form>
    <h2>授权测试说明</h2><p>仅测试当前实例中的客户资料访问边界，不要对外部系统发起请求。</p>""")


@app.post("/login")
def login():
    data = request.form or (request.get_json(silent=True) or {})
    username = data.get("username")
    if not username or users.get(username) != data.get("password"):
        return jsonify(error="invalid credentials"), 401
    token = secrets.token_urlsafe(18)
    sessions[token] = username
    response = make_response(redirect(url_for("me")))
    response.set_cookie("session", token, httponly=True)
    return response


@app.get("/me")
def me():
    user = current_user()
    if not user:
        return redirect("/")
    profile = profiles["customer-demo"]
    return page("我的资料", f"<p>当前用户：<b>{escape(user)}</b></p><p>客户：{escape(profile['name'])}</p>"
                f"<p><a href='/profiles/{quote('customer-demo')}'>查看资料详情</a></p>")


@app.get("/workspace")
def workspace():
    user = current_user()
    if not user:
        return redirect("/")
    # This legitimate task reference makes the second profile identifier discoverable.
    return page("协作任务", "<p>待确认客户资料：北区重点客户</p>"
                "<p>请在授权范围内核对客户资料详情后完成任务。</p>"
                "<a href='/profiles/customer-north'>打开任务关联资料</a>")


@app.get("/activity")
def activity():
    if not current_user():
        return redirect("/")
    return page("最近访问", "<ul><li>查看我的资料</li><li>打开协作任务中的客户资料</li></ul>")


@app.get("/profiles/<profile_id>")
def profile(profile_id: str):
    if not current_user():
        return jsonify(error="authentication required"), 401
    profile_data = profiles.get(profile_id)
    if profile_data is None:
        return jsonify(error="profile not found"), 404
    # Intentional flaw: authentication is checked, ownership is not.
    result = {"id": profile_id, "name": profile_data["name"], "industry": profile_data["industry"], "note": profile_data["note"]}
    if profile_id == "customer-north":
        result["note"] += FLAG
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
