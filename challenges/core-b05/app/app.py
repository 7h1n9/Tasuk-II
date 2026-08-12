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
logger = logging.getLogger("core-b05")
logging.basicConfig(level=logging.INFO, format="%(message)s")

rng = random.Random(SEED)
own_file_id = f"FILE-2026-{rng.randrange(1000, 9000):04d}"
internal_file_id = f"FILE-2026-{rng.randrange(1000, 9000):04d}"
while internal_file_id == own_file_id:
    internal_file_id = f"FILE-2026-{rng.randrange(1000, 9000):04d}"

sessions: dict[str, str] = {}
files: dict[str, dict[str, str | bool]] = {
    internal_file_id: {
        "file_id": internal_file_id,
        "owner": "人事复核员",
        "filename": "在职证明复核记录.txt",
        "content": "人事内部复核：任职资格已确认。\n处理结论：仅限内部查看。",
        "status": "已通过",
        "category": "内部复核",
        "preview_token": secrets.token_urlsafe(20),
        "internal": True,
    }
}


def event(name: str, **fields: str) -> None:
    logger.info(json.dumps({
        "event": name,
        "challenge_id": "core-b05",
        "instance_id": INSTANCE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields,
    }, ensure_ascii=False))


def current_user() -> str | None:
    return sessions.get(request.cookies.get("session", ""))


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/") or request.path.startswith("/preview/") or request.path.startswith("/download/"):
                return jsonify(error="authentication required"), 401
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


def page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>{html.escape(title)}</title>
    <style>body{{font:16px system-ui;max-width:980px;margin:38px auto;background:#f4f7fb;color:#172033}}
    main{{background:#fff;padding:28px;border-radius:15px;box-shadow:0 8px 28px #17203318}}
    nav{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:22px}}a{{color:#145db5}}
    input,button{{padding:9px;margin:4px;border:1px solid #bdc8d8;border-radius:7px;font:inherit}}
    button{{background:#145db5;color:#fff}}table{{width:100%;border-collapse:collapse}}
    td,th{{padding:10px;border-bottom:1px solid #e6eaf0;text-align:left}}
    .notice{{padding:13px;background:#eef5ff;border-radius:9px}}code{{background:#f0f2f5;padding:2px 5px;border-radius:4px}}
    pre{{white-space:pre-wrap;background:#f7f8fa;padding:15px;border-radius:9px}}</style>
    <main><h1>{html.escape(title)}</h1><nav><a href='/dashboard'>工作台</a>
    <a href='/profile'>员工资料</a><a href='/upload'>上传文件</a><a href='/files'>我的文件</a>
    <a href='/help'>使用说明</a></nav>{body}</main></html>"""


def public_file(item: dict[str, str | bool]) -> dict[str, str]:
    return {key: str(item[key]) for key in ("file_id", "filename", "status", "category")}


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-b05")


@app.get("/")
def index():
    return page("员工资料文件管理中心", """
      <p>员工可以上传资料、查看处理状态、预览审核副本并下载自己的文件。</p>
      <div class='notice'><strong>演示账号：</strong> <code>employee</code> / <code>employee-pass</code><br>
      正常流程：登录、上传、查看审核状态、预览，然后下载。</div>
      <form method='post' action='/login'><label>账号 <input name='username' required></label>
      <label>密码 <input type='password' name='password' required></label><button>登录</button></form>
      <p>本题只处理无害文本文件。上传内容会经过转义后显示，不会被执行。</p>""")


@app.post("/login")
def login():
    data = request.form or (request.get_json(silent=True) or {})
    if data.get("username") != "employee" or data.get("password") != "employee-pass":
        return jsonify(error="invalid credentials"), 401
    token = secrets.token_urlsafe(18)
    sessions[token] = "employee"
    event("login_success")
    response = make_response(redirect(url_for("dashboard")))
    response.set_cookie("session", token, httponly=True, samesite="Lax")
    return response


@app.get("/dashboard")
@require_login
def dashboard():
    return page("员工文件管理中心", """
      <p>先在员工资料页确认账号，再上传一个小型文件并查看处理状态。</p>
      <ul><li><a href='/profile'>员工资料</a></li><li><a href='/upload'>上传文件</a></li>
      <li><a href='/files'>查看文件和处理通知</a></li></ul>""")


@app.get("/profile")
@require_login
def profile():
    return page("员工资料", """
      <dl><dt>员工账号</dt><dd>employee</dd><dt>所属部门</dt><dd>人事运营部</dd>
      <dt>文件规则</dt><dd>文件审核后会生成文本预览副本。</dd></dl>
      <p><a href='/upload'>开始正常上传</a></p>""")


@app.get("/upload")
@require_login
def upload_page():
    return page("上传文件", """
      <form method='post' action='/api/files' enctype='multipart/form-data'>
      <label>文件 <input type='file' name='file' required></label><button>上传并提交审核</button></form>
      <p>本题允许上传小型文本类文件，系统会在审核流程中生成预览。</p>""")


@app.get("/files")
@require_login
def file_list():
    own = [item for item in files.values() if item["owner"] == current_user()]
    rows = "".join(
        f"<tr><td><code>{html.escape(str(item['file_id']))}</code></td>"
        f"<td>{html.escape(str(item['filename']))}</td><td>{html.escape(str(item['status']))}</td>"
        f"<td><a href='/api/files/{html.escape(str(item['file_id']))}/processing'>Processing details</a></td></tr>"
        for item in own
    ) or "<tr><td colspan='4'>No uploaded files yet.</td></tr>"
    notice = f"""<div class='notice'><strong>审核动态</strong><br>
      共享处理队列记录了一份已通过的内部复核文件，编号为
      <code>{html.escape(internal_file_id)}</code>。可以通过文件处理详情查看该文件的预览状态。</div>"""
    return page("我的文件", f"""<table><tr><th>文件编号</th><th>文件名</th><th>状态</th><th>处理流程</th></tr>{rows}</table>
      {notice}<p>表格只列出你的文件，审核动态中的编号来自独立的文件处理记录。</p>""")


@app.get("/help")
@require_login
def help_page():
    return page("文件处理说明", """
      <p>上传后可以通过处理详情响应找到预览地址。预览用于查看审核副本，下载功能仍限制为文件所有者。</p>
      <p>打开预览前，请将处理详情中的所有者与当前员工资料进行对比。</p>""")


@app.post("/api/files")
@require_login
def create_file():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify(error="file is required"), 400
    filename = os.path.basename(uploaded.filename)[:80]
    content = uploaded.read(16 * 1024 + 1)
    if len(content) > 16 * 1024:
        return jsonify(error="file too large"), 413
    file_id = f"FILE-2026-{rng.randrange(1000, 9000):04d}"
    while file_id in files:
        file_id = f"FILE-2026-{rng.randrange(1000, 9000):04d}"
    item = {
        "file_id": file_id,
        "owner": current_user() or "employee",
        "filename": filename,
        "content": content.decode("utf-8", errors="replace"),
        "status": "待复核",
        "category": "员工上传",
        "preview_token": secrets.token_urlsafe(20),
        "internal": False,
    }
    files[file_id] = item
    event("file_uploaded", file_id=file_id)
    return jsonify(file_id=file_id, status=item["status"], processing_url=f"/api/files/{file_id}/processing"), 201


@app.get("/api/files/<file_id>/processing")
@require_login
def processing(file_id: str):
    item = files.get(file_id)
    if item is None:
        return jsonify(error="未找到文件"), 404
    event("file_processing_view", file_id=file_id)
    # The processing queue is visible to logged-in employees, but it does not
    # apply an owner check before returning a preview capability.
    return jsonify(file=public_file(item), owner=str(item["owner"]), status=item["status"],
                   preview_url=f"/preview/{item['preview_token']}")


@app.get("/preview/<token>")
@require_login
def preview(token: str):
    item = next((candidate for candidate in files.values() if candidate["preview_token"] == token), None)
    if item is None:
        return "未找到预览", 404
    event("file_preview", file_id=str(item["file_id"]))
    body = f"预览副本\n文件：{item['filename']}\n所有者：{item['owner']}\n\n{item['content']}"
    if item["internal"]:
        body += f"\n\n内部复核处理结论：{FLAG}"
    return f"<pre>{html.escape(body)}</pre>", 200, {"Content-Type": "text/html; charset=utf-8"}


@app.get("/download/<token>")
@require_login
def download(token: str):
    item = next((candidate for candidate in files.values() if candidate["preview_token"] == token), None)
    if item is None:
        return "未找到文件", 404
    if item["owner"] != current_user():
        return jsonify(error="仅文件所有者可以下载"), 403
    event("file_download", file_id=str(item["file_id"]))
    return str(item["content"]), 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
