from __future__ import annotations

import os
import sqlite3
from html import escape

from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = os.getenv("INSTANCE_FLAG", "flag{missing}")


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript("""
      CREATE TABLE inventory (id INTEGER, name TEXT, department TEXT, status TEXT);
      INSERT INTO inventory VALUES (1, '便携式终端', '销售部', '在库');
      INSERT INTO inventory VALUES (2, '会议摄像头', '市场部', '借出');
      INSERT INTO inventory VALUES (3, '无线交换机', '网络部', '在库');
      CREATE TABLE settings (key TEXT, value TEXT);
    """)
    connection.execute("INSERT INTO settings VALUES (?, ?)", ("maintenance_note", FLAG))
    return connection


def layout(body: str) -> str:
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>内部物资检索平台</title>
    <style>body{{font:16px system-ui;max-width:900px;margin:40px auto;background:#f5f7fb;color:#172033}}
    main{{background:#fff;padding:28px;border-radius:14px;box-shadow:0 8px 30px #17203318}}
    nav{{display:flex;gap:18px;margin-bottom:20px}}a{{color:#1565c0}}input,select{{padding:8px;margin-right:8px}}</style>
    <main><h1>内部物资检索平台</h1><nav><a href='/'>首页</a><a href='/search'>物资检索</a><a href='/help'>查询帮助</a><a href='/inventory'>库存状态</a></nav>{body}</main></html>"""


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-b01")


@app.get("/")
def index():
    return layout("""
    <p>面向员工的设备、部门和库存状态检索服务。</p>
    <h2>可用业务</h2><ul><li>按关键词查找设备</li><li>按部门筛选</li><li>查看库存状态</li></ul>
    <p><a href='/search'>开始一次物资检索</a>　<a href='/help'>查看查询帮助</a></p>
    <p><small>授权说明：仅测试当前演示实例的查询边界。</small></p>""")


@app.get("/help")
def help_page():
    return layout("<h2>查询帮助</h2><p>关键词、部门和状态可以组合使用；空值表示不限制该条件。</p>"
                  "<p>页面结果来自检索服务，异常输入请在授权范围内记录并分析。</p>")


@app.get("/inventory")
def inventory():
    return layout("<h2>库存状态</h2><p>库存状态由检索服务统一提供，请使用检索页查看设备。</p>")


@app.get("/search")
def search():
    keyword = request.args.get("q", "")
    department = request.args.get("department", "")
    status = request.args.get("status", "")
    if request.args.get("format") == "json" or request.headers.get("Accept") == "application/json":
        connection = db()
        # Intentional flaw: q is concatenated into a business search query.
        sql = "SELECT id, name, department, status FROM inventory WHERE name LIKE '%" + keyword + "%'"
        if department:
            sql += " AND department = ?"
            rows = connection.execute(sql, (department,)).fetchall()
        else:
            rows = connection.execute(sql).fetchall()
        if status:
            rows = [row for row in rows if row["status"] == status]
        return jsonify(items=[dict(row) for row in rows], count=len(rows))
    return layout(f"""<h2>物资检索</h2><form><input name='q' placeholder='设备关键词' value='{escape(keyword)}'>
      <select name='department'><option value=''>全部部门</option><option>销售部</option><option>市场部</option><option>网络部</option></select>
      <select name='status'><option value=''>全部状态</option><option>在库</option><option>借出</option></select>
      <button>查询</button></form><p>也可通过 <code>?format=json</code> 查看检索结果。</p>""")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
