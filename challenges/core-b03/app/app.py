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
logger = logging.getLogger("core-b03")
logging.basicConfig(level=logging.INFO, format="%(message)s")

rng = random.Random(SEED)
public_doc_id = f"KB-2026-{rng.randrange(1000, 9000):04d}"
guide_doc_id = f"KB-2026-{rng.randrange(1000, 9000):04d}"
archived_doc_id = f"KB-2026-{rng.randrange(1000, 9000):04d}"
while len({public_doc_id, guide_doc_id, archived_doc_id}) != 3:
    archived_doc_id = f"KB-2026-{rng.randrange(1000, 9000):04d}"
public_attachment = secrets.token_urlsafe(18)
archived_attachment = secrets.token_urlsafe(18)
sessions: dict[str, str] = {}

documents = {
    public_doc_id: {
        "title": "知识库发布流程",
        "status": "published",
        "category": "运营规范",
        "keywords": ["知识库", "发布", "流程"],
        "summary": "面向员工的知识文章发布与复核流程。",
        "body": "文章提交后由内容管理员复核，发布版本会保留历史记录。",
        "attachment": public_attachment,
        "attachment_name": "publishing-guide.pdf",
        "attachment_body": "Knowledge Base Publishing Guide\nRevision: public\n",
    },
    guide_doc_id: {
        "title": "终端安全操作指南",
        "status": "published",
        "category": "信息安全",
        "keywords": ["安全", "终端", "指南"],
        "summary": "企业终端安全配置和日常操作说明。",
        "body": "请按照终端安全基线完成补丁、锁屏和日志配置。",
        "attachment": public_attachment,
        "attachment_name": "endpoint-guide.pdf",
        "attachment_body": "Endpoint Security Guide\nRevision: public\n",
    },
    archived_doc_id: {
        "title": "2026年度安全审计报告",
        "status": "archived",
        "category": "内部审计",
        "keywords": ["安全", "审计", "年度", "风险"],
        "summary": "已归档的年度安全审计资料，供内部复核使用。",
        "body": "该报告记录年度审计发现、风险处置和内部复核结论。",
        "attachment": archived_attachment,
        "attachment_name": "audit-report.pdf",
        "attachment_body": None,
    },
}


def event(name: str) -> None:
    logger.info(json.dumps({
        "event": name,
        "challenge_id": "core-b03",
        "instance_id": INSTANCE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False))


def current_user() -> str | None:
    return sessions.get(request.cookies.get("session", ""))


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/") or request.path.startswith("/download/"):
                return jsonify(error="authentication required"), 401
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


def page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>{html.escape(title)}</title>
    <style>body{{font:16px system-ui;max-width:960px;margin:38px auto;background:#f4f7fb;color:#172033}}
    main{{background:#fff;padding:28px;border-radius:15px;box-shadow:0 8px 28px #17203318}}
    nav{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:22px}}a{{color:#145db5}}
    input,button{{padding:9px;margin:4px;border:1px solid #bdc8d8;border-radius:7px;font:inherit}}
    button{{background:#145db5;color:#fff}}table{{width:100%;border-collapse:collapse}}
    td,th{{padding:10px;border-bottom:1px solid #e6eaf0;text-align:left}}
    .notice{{padding:13px;background:#eef5ff;border-radius:9px}}code{{background:#f0f2f5;padding:2px 5px;border-radius:4px}}
    </style><main><h1>{html.escape(title)}</h1><nav><a href='/dashboard'>工作台</a>
    <a href='/documents'>知识文档</a><a href='/search'>搜索</a><a href='/help'>使用说明</a></nav>{body}</main></html>"""


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-b03")


@app.get("/")
def index():
    return page("企业知识库文档平台", """
      <p>企业员工可以浏览知识文章、搜索资料、查看文档详情和下载附件。</p>
      <div class='notice'><strong>演示账号</strong>：<code>demo</code> / <code>demo-pass</code><br>
      文档列表默认展示当前知识库中的已发布文章。</div>
      <form method='post' action='/login'><label>账号 <input name='username' required></label>
      <label>密码 <input type='password' name='password' required></label><button>登录</button></form>
      <p>授权测试范围：仅检查当前实例中的知识文档索引和附件访问。</p>""")


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
    return page("知识库工作台", """
      <p>欢迎进入企业知识库。</p><ul><li><a href='/documents'>浏览已发布知识文章</a></li>
      <li><a href='/search'>搜索知识库</a></li><li><a href='/help'>查看使用说明</a></li></ul>""")


@app.get("/help")
@require_login
def help_page():
    return page("知识库使用说明", """
      <p>文档中心默认展示已发布文章。搜索可以按标题、摘要和业务关键词查找知识内容。</p>
      <p>文档详情会显示文档状态、版本和可下载附件。搜索结果来自历史索引，结果状态需要结合详情页确认。</p>
      <p>建议先浏览列表中的正常文章，再使用“安全”等业务关键词进行搜索。</p>""")


@app.get("/documents")
@require_login
def document_list():
    event("document_list_viewed")
    rows = "".join(
        f"<tr><td><a href='/documents/{html.escape(doc_id)}'>{html.escape(doc_id)}</a></td>"
        f"<td>{html.escape(doc['title'])}</td><td>{html.escape(doc['category'])}</td></tr>"
        for doc_id, doc in documents.items() if doc["status"] == "published"
    )
    return page("知识文档", f"<p>当前列表展示已发布文章。</p><table><tr><th>编号</th><th>标题</th><th>分类</th></tr>{rows}</table>")


@app.get("/search")
@require_login
def search_page():
    return page("知识库搜索", """
      <p>输入主题词查找知识文章，例如：发布、安全、风险。</p>
      <form method='get' action='/search'><input name='q' placeholder='输入关键词'><button>搜索</button></form>
      <div id='results'>搜索结果将在这里显示。</div>
      <script>const q=new URLSearchParams(location.search).get('q');
      if(q) fetch('/api/search?q='+encodeURIComponent(q)).then(r=>r.json()).then(data=>{
        document.getElementById('results').innerHTML='<pre>'+JSON.stringify(data.items,null,2)+'</pre>';
      });</script>""")


@app.get("/api/search")
@require_login
def search_api():
    query = str(request.args.get("q", "")).strip().lower()[:80]
    event("document_search")
    if not query:
        return jsonify(items=[])
    items = []
    for doc_id, doc in documents.items():
        haystack = " ".join([doc["title"], doc["summary"], *doc["keywords"]]).lower()
        if query in haystack:
            # Intentional stale-index disclosure: archived records are not
            # removed from the search index when list visibility changes.
            items.append({"document_id": doc_id, "title": doc["title"], "category": doc["category"],
                          "status": doc["status"], "snippet": doc["summary"]})
    return jsonify(query=query, items=items)


@app.get("/documents/<document_id>")
@require_login
def document_detail(document_id: str):
    doc = documents.get(document_id)
    if doc is None:
        return "document not found", 404
    event("document_view")
    return page("文档详情", f"""
      <p>文档编号：<code>{html.escape(document_id)}</code></p>
      <p>标题：{html.escape(doc['title'])}</p><p>状态：{html.escape(doc['status'])}</p>
      <p>分类：{html.escape(doc['category'])}</p><p>{html.escape(doc['body'])}</p>
      <p>附件：<a href='/download/{html.escape(doc['attachment'])}'>{html.escape(doc['attachment_name'])}</a></p>""")


@app.get("/download/<token>")
@require_login
def download(token: str):
    matched = next((doc for doc in documents.values() if doc["attachment"] == token), None)
    if matched is None:
        return "attachment not found", 404
    event("attachment_download")
    body = matched["attachment_body"]
    if body is None:
        body = f"Confidential Security Audit Report\nDocument: {archived_doc_id}\nFinding: {FLAG}\n"
    return body, 200, {"Content-Type": "application/pdf; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
