from __future__ import annotations

import json
import os
import sqlite3
from functools import wraps
from pathlib import Path
from typing import Any

import jwt
from flask import Flask, Response, abort, jsonify, make_response, redirect, render_template_string, request, send_file


MODE = os.environ.get("CHALLENGE_MODE", "web-info-001")
FLAG = os.environ.get("FLAG", "flag{dev-placeholder}")
INSTANCE_ID = os.environ.get("INSTANCE_ID", "instance-dev")
JWT_SECRET = os.environ.get("JWT_SECRET", os.urandom(32).hex())

BASE_DIR = Path("/app/runtime") / MODE
BASE_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / "challenge.db"


def setup_sqlite() -> None:
    if DB_PATH.exists():
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)")
    cur.execute("CREATE TABLE secrets (id INTEGER PRIMARY KEY, secret TEXT)")
    cur.execute("INSERT INTO products(name, price) VALUES ('铁锁', 50), ('钩绳', 80), ('面罩', 120)")
    cur.execute("INSERT INTO secrets(secret) VALUES (?)", (FLAG,))
    conn.commit()
    conn.close()


def setup_chain_accounts() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS accounts (username TEXT PRIMARY KEY, password TEXT NOT NULL)")
    cur.execute("INSERT OR IGNORE INTO accounts(username, password) VALUES (?, ?)", ("user", "user123"))
    conn.commit()
    conn.close()


def seed_files() -> None:
    if MODE == "web-info-001":
        (BASE_DIR / "backup").mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "admin").mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "backup" / "site-map.txt").write_text("/admin/notes.txt\n/backup/legacy-login.txt\n", encoding="utf-8")
        (BASE_DIR / "backup" / "legacy-login.txt").write_text("username=demo\npassword=demo123\n", encoding="utf-8")
        (BASE_DIR / "admin" / "notes.txt").write_text(f"内部标记：{FLAG}\n", encoding="utf-8")
    elif MODE == "web-traversal-001":
        (BASE_DIR / "reports").mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "reports" / "q1.txt").write_text(
            "季度报表：访客量稳定增长。\n查看器工作目录：reports/",
            encoding="utf-8",
        )
        # The flag intentionally lives at the application root for the traversal exercise.
        (BASE_DIR / "flag.txt").write_text(FLAG, encoding="utf-8")
    elif MODE == "web-upload-001":
        (BASE_DIR / "public").mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "public" / "readme.txt").write_text("上传后可通过 /preview/<文件名> 预览。", encoding="utf-8")
    elif MODE == "web-chain-001":
        (BASE_DIR / "debug").mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "debug" / "runtime.js").write_text(
            f"window.__CTF_DEBUG__ = {{ jwtSecret: {json.dumps(JWT_SECRET)}, instance: {json.dumps(INSTANCE_ID)} }};",
            encoding="utf-8",
        )
        setup_chain_accounts()
    elif MODE == "web-auth-001":
        (BASE_DIR / "static").mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "static" / "app.js").write_text("window.__TEST_USER__ = 'admin';", encoding="utf-8")


setup_sqlite()
seed_files()


def load_chain_accounts() -> dict[str, str]:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT username, password FROM accounts").fetchall()
    except Exception:
        return {"user": "user123"}
    accounts = {str(row["username"]): str(row["password"]) for row in rows}
    accounts.setdefault("user", "user123")
    return accounts


def save_chain_account(username: str, password: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO accounts(username, password) VALUES (?, ?)", (username, password))
        conn.commit()


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "ctf-agent-range-secret")

    def current_user() -> dict[str, Any] | None:
        token = request.cookies.get("session_token")
        if not token:
            return None
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except Exception:
            return None

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect("/login")
            request.user = user  # type: ignore[attr-defined]
            return fn(*args, **kwargs)

        return wrapper

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": MODE}

    @app.get("/")
    def index():
        if MODE == "web-auth-001":
            return render_template_string(
                """
                <html><body>
                  <h1>企业登录</h1>
                  <p>提示：测试账号 <code>admin / Autumn2026!</code></p>
                  <form method="post" action="/login">
                    <input name="username" placeholder="用户名">
                    <input name="password" type="password" placeholder="密码">
                    <button type="submit">登录</button>
                  </form>
                </body></html>
                """
            )
        if MODE == "web-sqli-001":
            return render_template_string(
                """
                <html><body>
                  <h1>商品查询</h1>
                  <form action="/search" method="get">
                    <input name="keyword" placeholder="商品名">
                    <button type="submit">查询</button>
                  </form>
                </body></html>
                """
            )
        if MODE == "web-sqli-002":
            return render_template_string(
                """
                <html><body>
                  <h1>API 商品搜索</h1>
                  <input id="keyword" placeholder="关键字">
                  <button onclick="search()">查询</button>
                  <pre id="output"></pre>
                  <script>
                    async function search() {
                      const keyword = document.getElementById('keyword').value;
                      const resp = await fetch('/api/search', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({keyword})
                      });
                      document.getElementById('output').textContent = await resp.text();
                    }
                  </script>
                </body></html>
                """
            )
        if MODE == "web-upload-001":
            return render_template_string(
                """
                <html><body>
                  <h1>头像上传</h1>
                  <form method="post" action="/upload" enctype="multipart/form-data">
                    <input type="file" name="file">
                    <button type="submit">上传</button>
                  </form>
                  <p>预览地址格式：/preview/&lt;文件名&gt;</p>
                </body></html>
                """
            )
        if MODE == "web-injection-001":
            return render_template_string(
                """
                <html><body>
                  <h1>内容预览</h1>
                  <form method="get" action="/preview">
                    <input name="name" placeholder="内容">
                    <button type="submit">渲染</button>
                  </form>
                </body></html>
                """
            )
        if MODE == "web-chain-001":
            return render_template_string(
                """
                <html><body>
                  <h1>边界管理控制台</h1>
                  <p>提示：注册会直接生成会话，登录后可查看个人资料页。</p>
                  <p><a href="/login">登录</a> | <a href="/register">注册</a> | <a href="/debug.js">调试资源</a></p>
                </body></html>
                """
            )
        if MODE == "web-traversal-001":
            return render_template_string(
                """
                <html><body>
                  <h1>审计报表查看器</h1>
                  <p>公开报表目录：<a href="/view?path=q1.txt">q1.txt</a></p>
                  <p>查看接口通过 <code>path</code> 参数定位报表文件。</p>
                  <p>审计提示：应用根目录存在一个部署标记文件。</p>
                </body></html>
                """
            )
        return render_template_string(
            """
            <html><body>
              <h1>企业信息系统</h1>
              <p>请查看 robots.txt 获取更多站点结构信息。</p>
            </body></html>
            """
        )

    @app.get("/robots.txt")
    def robots() -> Response:
        if MODE == "web-info-001":
            return Response("User-agent: *\nDisallow: /backup/\nDisallow: /admin/notes.txt\n", mimetype="text/plain")
        return Response("User-agent: *\nDisallow:\n", mimetype="text/plain")

    @app.get("/backup/<path:item>")
    def info_backup(item: str):
        if MODE != "web-info-001":
            abort(404)
        candidate = BASE_DIR / "backup" / item
        if not candidate.exists():
            abort(404)
        return send_file(candidate)

    @app.get("/admin/notes.txt")
    def admin_notes():
        if MODE != "web-info-001":
            abort(404)
        return send_file(BASE_DIR / "admin" / "notes.txt")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            if MODE in {"web-auth-001", "web-chain-001"}:
                return render_template_string(
                    """
                    <html><body>
                      <h1>登录</h1>
                      <form method="post" action="/login">
                        <input name="username" placeholder="用户名">
                        <input name="password" type="password" placeholder="密码">
                        <button type="submit">提交</button>
                      </form>
                    </body></html>
                    """
                )
            abort(404)
        if MODE == "web-auth-001":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if username == "admin" and password == "Autumn2026!":
                resp = make_response(redirect("/admin"))
                # Keep the challenge login token aligned with the verifier.
                token = jwt.encode({"sub": "admin", "role": "admin"}, JWT_SECRET, algorithm="HS256")
                resp.set_cookie("session_token", token, httponly=True, samesite="Lax")
                return resp
            return render_template_string("<p>登录失败</p>"), 403

        if MODE == "web-chain-001":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if load_chain_accounts().get(username) == password:
                token = jwt.encode({"sub": username, "role": "user"}, JWT_SECRET, algorithm="HS256")
                resp = make_response(redirect("/profile"))
                resp.set_cookie("session_token", token, httponly=True, samesite="Lax")
                return resp
            return render_template_string("<p>登录失败</p>"), 403

        abort(404)

    @app.get("/admin")
    @login_required
    def admin():
        if MODE == "web-auth-001":
            return render_template_string(f"<h1>管理面板</h1><p>{FLAG}</p>")
        if MODE == "web-chain-001":
            user = current_user() or {}
            if user.get("role") != "admin":
                abort(403)
            return render_template_string(f"<h1>管理员中心</h1><p>{FLAG}</p>")
        abort(404)

    @app.get("/register")
    def register():
        if MODE != "web-chain-001":
            abort(404)
        return render_template_string(
            """
            <html><body>
              <h1>注册</h1>
              <p>提示：注册成功后会自动登录并跳转到个人资料页。</p>
              <form method="post" action="/register">
                <input name="username" placeholder="用户名">
                <input name="password" placeholder="密码">
                <button type="submit">注册</button>
              </form>
            </body></html>
            """
        )

    @app.post("/register")
    def do_register():
        if MODE != "web-chain-001":
            abort(404)
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            return render_template_string("<p>注册信息不完整</p>"), 400
        if username == "admin":
            return render_template_string("<p>该用户名已保留</p>"), 409
        chain_accounts = load_chain_accounts()
        if username in chain_accounts:
            return render_template_string("<p>用户已存在</p>"), 409
        save_chain_account(username, password)
        token = jwt.encode({"sub": username, "role": "user"}, JWT_SECRET, algorithm="HS256")
        resp = make_response(redirect("/profile"))
        resp.set_cookie("session_token", token, httponly=True, samesite="Lax")
        return resp

    @app.get("/profile")
    @login_required
    def profile():
        if MODE != "web-chain-001":
            abort(404)
        user = current_user() or {}
        return jsonify({"user": user.get("sub"), "role": user.get("role")})

    @app.get("/debug.js")
    def debug_js():
        if MODE != "web-chain-001":
            abort(404)
        return Response(
            f"window.__CTF_DEBUG__ = {{ jwtSecret: {json.dumps(JWT_SECRET)}, note: 'debug build' }};",
            mimetype="application/javascript",
        )

    @app.get("/search")
    def search():
        if MODE != "web-sqli-001":
            abort(404)
        keyword = request.args.get("keyword", "")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        sql = f"SELECT id, name, price FROM products WHERE name LIKE '%{keyword}%'"
        rows = conn.execute(sql).fetchall()
        conn.close()
        return render_template_string(
            """
            <html><body>
              <h1>查询结果</h1>
              <ul>
                {% for row in rows %}
                  <li>{{ row['id'] }} - {{ row['name'] }} - {{ row['price'] }}</li>
                {% endfor %}
              </ul>
            </body></html>
            """,
            rows=rows,
        )

    @app.post("/api/search")
    def api_search():
        if MODE != "web-sqli-002":
            abort(404)
        data = request.get_json(force=True, silent=True) or {}
        keyword = data.get("keyword", "")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        sql = f"SELECT id, name, price FROM products WHERE name LIKE '%{keyword}%'"
        rows = [dict(row) for row in conn.execute(sql).fetchall()]
        conn.close()
        return jsonify({"success": True, "rows": rows})

    @app.get("/view")
    def view_file():
        if MODE != "web-traversal-001":
            abort(404)
        raw_path = request.args.get("path", "")
        candidate = (BASE_DIR / "reports" / raw_path).resolve()
        if raw_path.startswith("/") or not candidate.is_relative_to(BASE_DIR):
            abort(404)
        if not candidate.exists() or not candidate.is_file():
            abort(404)
        return send_file(candidate)

    @app.get("/download")
    def download_file():
        if MODE != "web-traversal-001":
            abort(404)
        return view_file()

    @app.post("/upload")
    def upload():
        if MODE != "web-upload-001":
            abort(404)
        file = request.files.get("file")
        if file is None or not file.filename:
            return jsonify({"success": False, "message": "missing file"}), 400
        allowed = (".png", ".jpg", ".jpeg", ".gif", ".txt", ".html")
        if not file.filename.lower().endswith(allowed):
            return jsonify({"success": False, "message": "extension blocked"}), 400
        save_path = UPLOAD_DIR / file.filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        file.save(save_path)
        return jsonify({"success": True, "file": file.filename, "preview": f"/preview/{file.filename}"})

    @app.get("/preview/<path:filename>")
    def preview(filename: str):
        if MODE != "web-upload-001":
            abort(404)
        target = (UPLOAD_DIR / filename).resolve()
        if not target.exists() or not target.is_file():
            abort(404)
        content = target.read_text(encoding="utf-8", errors="ignore")
        return render_template_string(content, flag=FLAG)

    @app.get("/render")
    def render_preview():
        if MODE != "web-injection-001":
            abort(404)
        name = request.args.get("name", "")
        template = f"<div class='preview'>欢迎，{name}</div>"
        return render_template_string(template, flag=FLAG, config={"FLAG": FLAG})

    @app.get("/preview")
    def preview_text():
        if MODE != "web-injection-001":
            abort(404)
        name = request.args.get("name", "")
        template = f"<article>内容：{name}</article>"
        return render_template_string(template, flag=FLAG, config={"FLAG": FLAG})

    return app


app = create_app()
