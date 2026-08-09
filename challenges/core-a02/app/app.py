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
logger = logging.getLogger("core-a02")
logging.basicConfig(level=logging.INFO, format="%(message)s")

rng = random.Random(SEED)
own_order_no = f"PO-2026-{rng.randrange(1000, 9000):04d}"
foreign_order_no = f"PO-2026-{(int(own_order_no[-4:]) + 137) % 9000 + 1000:04d}"
attachment_token = secrets.token_urlsafe(20)
sessions: dict[str, str] = {}

orders = {
    own_order_no: {
        "owner": "demo",
        "owner_display": "研发部演示员工",
        "department": "研发部",
        "supplier": "华东办公设备有限公司",
        "status": "采购中",
        "summary": "研发部门显示器和扩展坞采购申请。",
    },
    foreign_order_no: {
        "owner": "finance-demo",
        "owner_display": "财务部采购专员",
        "department": "财务部",
        "supplier": "北辰安全设备有限公司",
        "status": "内部验收",
        "summary": "财务终端安全设备采购及内部验收订单。",
    },
}


def event(name: str) -> None:
    logger.info(json.dumps({
        "event": name,
        "challenge_id": "core-a02",
        "instance_id": INSTANCE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False))


def current_user() -> str | None:
    return sessions.get(request.cookies.get("session", ""))


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/") or request.path.startswith("/attachments/"):
                return jsonify(error="authentication required"), 401
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


def page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'>
    <title>{html.escape(title)}</title><style>
    body{{font:16px system-ui;max-width:960px;margin:38px auto;background:#f4f7fb;color:#172033}}
    main{{background:#fff;padding:28px;border-radius:15px;box-shadow:0 8px 28px #17203318}}
    nav{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:22px}}a{{color:#145db5}}
    input,button{{padding:9px;margin:4px;border:1px solid #bdc8d8;border-radius:7px;font:inherit}}
    button{{background:#145db5;color:#fff}}table{{width:100%;border-collapse:collapse}}
    td,th{{padding:10px;border-bottom:1px solid #e6eaf0;text-align:left}}
    .notice{{padding:13px;background:#eef5ff;border-radius:9px}}
    code{{background:#f0f2f5;padding:2px 5px;border-radius:4px}}
    </style><main><h1>{html.escape(title)}</h1><nav>
    <a href='/dashboard'>工作台</a><a href='/orders'>我的采购</a>
    <a href='/announcements'>采购公告</a><a href='/help'>查询说明</a>
    </nav>{body}</main></html>"""


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-a02")


@app.get("/")
def index():
    return page("企业采购订单查询系统", """
      <p>员工可以查看本人采购申请、订单详情和物流进度，并下载订单附件。</p>
      <div class='notice'><strong>演示账号</strong>：<code>demo</code> / <code>demo-pass</code><br>
      订单详情会在业务页面加载时向查询接口请求数据。</div>
      <form method='post' action='/login'><label>账号 <input name='username' required></label>
      <label>密码 <input type='password' name='password' required></label><button>登录</button></form>
      <p>授权测试范围：仅检查当前采购系统实例中的订单访问边界。</p>""")


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
    return page("采购工作台", """
      <p>欢迎进入企业采购工作台。</p><ul>
      <li><a href='/orders'>我的采购订单</a>：查看本人订单和物流状态</li>
      <li><a href='/announcements'>采购公告</a>：查看供应商和物流通知</li>
      <li><a href='/help'>查询说明</a>：了解订单编号和附件下载规则</li></ul>""")


@app.get("/help")
@require_login
def help_page():
    return page("订单查询说明", """
      <p>订单编号采用 <code>PO-2026-xxxx</code> 格式。订单列表只显示当前账号提交的采购申请。</p>
      <p>订单详情页面会加载供应商、物流状态和可用附件信息。请先观察正常订单的页面请求。</p>
      <p>系统公告可能引用其他部门订单，以便员工跟进跨部门物流。</p>""")


@app.get("/orders")
@require_login
def order_list():
    event("own_order_list_viewed")
    order = orders[own_order_no]
    return page("我的采购订单", f"""
      <p>当前账号：研发部演示员工。列表仅展示本人采购申请。</p>
      <table><tr><th>订单编号</th><th>供应商</th><th>状态</th></tr>
      <tr><td><a href='/orders/{html.escape(own_order_no)}'>{html.escape(own_order_no)}</a></td>
      <td>{html.escape(order['supplier'])}</td><td>{html.escape(order['status'])}</td></tr></table>""")


@app.get("/orders/<order_id>")
@require_login
def order_detail_page(order_id: str):
    if order_id not in orders:
        return "订单不存在", 404
    if order_id == own_order_no:
        event("own_order_detail_viewed")
    return page("采购订单详情", f"""
      <p>订单编号：<code>{html.escape(order_id)}</code></p>
      <div id='order-detail'>正在加载订单信息……</div>
      <script>fetch('/api/orders/{html.escape(order_id)}').then(r=>r.json()).then(data=>{{
        const box=document.getElementById('order-detail');
        if(data.error){{box.textContent=data.error;return;}}
        box.innerHTML='<h2>'+data.supplier+'</h2><p>部门：'+data.department+'</p>'+
          '<p>状态：'+data.status+'</p><p>'+data.summary+'</p>'+
          (data.attachment ? '<p>订单附件：<a href="'+data.attachment.download_url+'">下载验收报告</a></p>' : '');
      }});</script>""")


@app.get("/announcements")
@require_login
def announcements():
    event("announcement_viewed")
    return page("采购公告", "<ul><li><a href='/announcements/2026-07'>跨部门物流通知</a></li></ul>")


@app.get("/announcements/2026-07")
@require_login
def announcement_detail():
    event("announcement_viewed")
    return page("跨部门物流通知", f"""
      <p>财务部的安全设备已进入内部验收，请相关协作人员关注订单进度。</p>
      <p>物流参考订单：<code>{html.escape(foreign_order_no)}</code></p>
      <p>如需确认验收信息，请通过订单查询页面查看详情。</p>""")


@app.get("/api/orders/<order_id>")
@require_login
def order_api(order_id: str):
    order = orders.get(order_id)
    if order is None:
        return jsonify(error="order not found"), 404
    # Intentional BOLA: the endpoint checks authentication but not order ownership.
    foreign = order_id != own_order_no
    if foreign:
        event("foreign_order_accessed")
    result = {"order_id": order_id, "department": order["department"], "supplier": order["supplier"],
              "status": order["status"], "summary": order["summary"]}
    if foreign:
        result["attachment"] = {"name": "internal-acceptance-report.txt", "download_url": f"/attachments/{attachment_token}"}
    return jsonify(result)


@app.get("/attachments/<token>")
@require_login
def attachment(token: str):
    if token != attachment_token:
        return "attachment not found", 404
    event("attachment_downloaded")
    body = f"Internal Procurement Acceptance Report\nOrder: {foreign_order_no}\nVerification: {FLAG}\n"
    return body, 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
