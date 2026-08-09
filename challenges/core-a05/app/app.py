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
logger = logging.getLogger("core-a05")
logging.basicConfig(level=logging.INFO, format="%(message)s")

rng = random.Random(SEED)
own_contract_no = f"CT-2026-{rng.randrange(1000, 9000):04d}"
foreign_contract_no = f"CT-2026-{(int(own_contract_no[-4:]) + 211) % 9000 + 1000:04d}"
attachment_token = secrets.token_urlsafe(20)
sessions: dict[str, dict[str, str]] = {}
contracts: dict[str, dict[str, str]] = {
    own_contract_no: {
        "owner": "submitter", "role": "submitter", "title": "研发办公设备年度采购合同",
        "status": "submitted", "counterparty": "华东办公设备有限公司",
    },
    foreign_contract_no: {
        "owner": "internal-procurement", "role": "reviewer", "title": "内部安全服务续约合同",
        "status": "approved", "counterparty": "北辰安全设备有限公司",
    },
}


def event(name: str) -> None:
    logger.info(json.dumps({
        "event": name,
        "challenge_id": "core-a05",
        "instance_id": INSTANCE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False))


def current_session() -> dict[str, str] | None:
    return sessions.get(request.cookies.get("session", ""))


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_session() is None:
            if request.path.startswith("/api/") or request.path.startswith("/attachments/"):
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
    textarea{{width:95%;min-height:100px}}button{{background:#145db5;color:#fff}}
    table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #e6eaf0;text-align:left}}
    .notice{{padding:13px;background:#eef5ff;border-radius:9px}}code{{background:#f0f2f5;padding:2px 5px;border-radius:4px}}
    </style><main><h1>{html.escape(title)}</h1><nav><a href='/contracts'>合同中心</a>
    <a href='/contracts/new'>提交合同</a><a href='/activity'>活动记录</a><a href='/profile'>个人资料</a><a href='/help'>流程说明</a></nav>{body}</main></html>"""


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-a05")


@app.get("/")
def index():
    return page("企业合同审核平台", """
      <p>合同提交人可以创建合同并跟踪审核状态，审核人员负责最终审批。</p>
      <div class='notice'><strong>演示账号</strong>：<code>submitter</code> / <code>submitter-pass</code><br>
      当前账号可以提交合同和查看本人合同状态。</div>
      <form method='post' action='/login'><label>账号 <input name='username' required></label>
      <label>密码 <input type='password' name='password' required></label><button>登录</button></form>
      <p>授权测试范围：仅检查当前合同审核实例的业务流程和附件访问边界。</p>""")


@app.post("/login")
def login():
    data = request.form or (request.get_json(silent=True) or {})
    credentials = {"submitter": ("submitter-pass", "submitter"), "reviewer": ("reviewer-pass", "reviewer")}
    record = credentials.get(str(data.get("username")))
    if not record or record[0] != data.get("password"):
        return jsonify(error="invalid credentials"), 401
    token = secrets.token_urlsafe(18)
    sessions[token] = {"user": str(data.get("username")), "role": record[1]}
    event("login_success")
    response = make_response(redirect(url_for("contract_list")))
    response.set_cookie("session", token, httponly=True, samesite="Lax")
    return response


@app.get("/help")
@require_login
def help_page():
    return page("审核流程说明", """
      <p>合同生命周期通常为：<code>draft</code> → <code>submitted</code> → <code>reviewing</code> → <code>approved</code>。</p>
      <p>提交人可以查看自己的状态，审核人员可以处理最终审核附件。</p>
      <p>活动记录会展示跨部门合同的流程节点，合同详情页会加载状态和审核结果。</p>""")


@app.get("/profile")
@require_login
def profile():
    user = current_session() or {}
    return page("个人资料", f"<p>用户：{html.escape(user.get('user', 'unknown'))}</p><p>角色：{html.escape(user.get('role', 'unknown'))}</p>")


@app.get("/contracts")
@require_login
def contract_list():
    event("contract_list_viewed")
    user = current_session()["user"]
    own = [(
        key, value) for key, value in contracts.items() if value["owner"] == user
    ]
    rows = "".join(f"<tr><td><a href='/contracts/{html.escape(key)}'>{html.escape(key)}</a></td>"
                   f"<td>{html.escape(value['title'])}</td><td>{html.escape(value['status'])}</td></tr>" for key, value in own)
    return page("我的合同", f"<p>当前账号只显示本人提交的合同。</p><table><tr><th>合同编号</th><th>标题</th><th>状态</th></tr>{rows}</table>")


@app.get("/contracts/new")
@require_login
def new_contract():
    return page("提交合同", """
      <form method='post' action='/api/contracts'><label>合同标题 <input name='title' value='新增采购合同'></label>
      <label>合同说明</label><textarea name='description'>请审核本次采购合同的条款。</textarea><button>提交审核</button></form>
      <p>提交后可在合同中心观察状态变化和后续请求。</p>""")


@app.post("/api/contracts")
@require_login
def create_contract():
    data = request.form or (request.get_json(silent=True) or {})
    user = current_session()["user"]
    if user != "submitter":
        return jsonify(error="only submitters can create contracts"), 403
    title = str(data.get("title", "新增采购合同"))[:100]
    new_no = f"CT-2026-{rng.randrange(1000, 9000):04d}"
    while new_no in contracts:
        new_no = f"CT-2026-{rng.randrange(1000, 9000):04d}"
    contracts[new_no] = {"owner": user, "role": "submitter", "title": title,
                         "status": "submitted", "counterparty": "演示供应商"}
    event("contract_submitted")
    if request.form:
        return redirect(url_for("contract_detail", contract_id=new_no))
    return jsonify(contract_id=new_no, status="submitted")


@app.get("/contracts/<contract_id>")
@require_login
def contract_detail(contract_id: str):
    contract = contracts.get(contract_id)
    if contract is None:
        return "contract not found", 404
    return page("合同详情", f"""
      <p>合同编号：<code>{html.escape(contract_id)}</code></p><p>标题：{html.escape(contract['title'])}</p>
      <p>对方：{html.escape(contract['counterparty'])}</p><div id='status'>正在加载审核状态……</div>
      <script>fetch('/api/contracts/{html.escape(contract_id)}/status').then(r=>r.json()).then(data=>{{
        document.getElementById('status').textContent='当前状态：'+(data.status||data.error);
      }});</script>""")


@app.get("/activity")
@require_login
def activity():
    event("activity_log_viewed")
    return page("审核活动记录", f"""
      <p>近期跨部门审核节点：</p><ul>
      <li>安全服务合同 <code>{html.escape(foreign_contract_no)}</code> 已完成最终审核。</li>
      <li>项目采购申请正在按流程排队。</li></ul>
      <p>如需查看详情，请从合同中心和状态接口确认当前流程阶段。</p>""")


@app.get("/api/contracts/<contract_id>/status")
@require_login
def contract_status(contract_id: str):
    contract = contracts.get(contract_id)
    if contract is None:
        return jsonify(error="contract not found"), 404
    event("contract_status_viewed")
    return jsonify(contract_id=contract_id, status=contract["status"], title=contract["title"])


@app.get("/api/contracts/<contract_id>/review")
@require_login
def review_result(contract_id: str):
    contract = contracts.get(contract_id)
    if contract is None:
        return jsonify(error="contract not found"), 404
    if contract["status"] != "approved":
        return jsonify(error="final review is not available for this status"), 409
    # Intentional workflow authorization flaw: status is checked, reviewer role is not.
    event("approved_review_result_accessed")
    return jsonify(contract_id=contract_id, status="approved", result="approved",
                   attachment={"name": "final-review-attachment.txt", "download_url": f"/attachments/{attachment_token}"})


@app.get("/attachments/<token>")
@require_login
def attachment(token: str):
    if token != attachment_token:
        return "attachment not found", 404
    event("final_attachment_downloaded")
    return f"Final Contract Review Attachment\nContract: {foreign_contract_no}\nApproval note: {FLAG}\n", 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
