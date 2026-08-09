from __future__ import annotations

import hashlib
import html
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from flask import Flask, jsonify, request


app = Flask(__name__)
SEED = os.getenv("VARIANT_SEED", "demo")
FLAG = os.getenv("INSTANCE_FLAG", "flag{missing}")
INSTANCE_ID = os.getenv("INSTANCE_ID", "unknown")
DATA_ROOT = Path("/app/data").resolve()
PUBLIC_ROOT = DATA_ROOT / "public"
PRIVATE_ROOT = DATA_ROOT / "private"
PRIVATE_FILENAME = f"review-2026-{hashlib.sha256(SEED.encode()).hexdigest()[:8]}.txt"
logger = logging.getLogger("core-c01")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def event(name: str) -> None:
    logger.info(json.dumps({
        "event": name,
        "challenge_id": "core-c01",
        "instance_id": INSTANCE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False))


def initialize_files() -> None:
    PUBLIC_ROOT.mkdir(parents=True, exist_ok=True)
    PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
    (PUBLIC_ROOT / "device-guide.txt").write_text(
        "办公设备使用指南\n请在办公网络内使用登记设备，并按部门规范提交维修申请。\n",
        encoding="utf-8",
    )
    (PUBLIC_ROOT / "meeting-policy.txt").write_text(
        "会议室预约规范\n预约后请按时使用，临时变更请在系统中更新记录。\n",
        encoding="utf-8",
    )
    archive_ref = f"private/{PRIVATE_FILENAME}"
    (PUBLIC_ROOT / "migration-record.txt").write_text(
        "历史客户端迁移记录\n"
        "旧版附件已经转入统一归档流程。\n"
        f"legacy_archive_ref: {archive_ref}\n"
        "该记录仅用于核对迁移批次。\n",
        encoding="utf-8",
    )
    (PUBLIC_ROOT / "manifest.json").write_text(
        json.dumps({"documents": ["device-guide.txt", "meeting-policy.txt", "migration-record.txt"], "legacy_archive_ref": archive_ref}, ensure_ascii=False),
        encoding="utf-8",
    )
    (PRIVATE_ROOT / PRIVATE_FILENAME).write_text(
        "内部复核归档\n来源：历史客户端迁移批次\n验证结果：通过\n" + FLAG + "\n",
        encoding="utf-8",
    )


initialize_files()


def layout(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'>
    <title>{html.escape(title)}</title>
    <style>
      body {{ max-width:960px; margin:36px auto; padding:0 18px; background:#f5f7fb; color:#182233; font:16px system-ui; }}
      main {{ background:#fff; border-radius:16px; padding:28px; box-shadow:0 8px 28px #1e293b18; }}
      nav {{ display:flex; gap:18px; flex-wrap:wrap; margin-bottom:24px; }} a {{ color:#145db5; }}
      li {{ margin:12px 0; }} .panel {{ padding:16px; background:#eef5ff; border-radius:10px; margin:14px 0; }} code {{ background:#f0f2f5; padding:2px 5px; border-radius:4px; }}
    </style><main><h1>{html.escape(title)}</h1>
    <nav><a href='/'>平台首页</a><a href='/documents'>公开文档</a><a href='/migration-notes'>迁移说明</a></nav>{body}</main></html>"""


DOCUMENTS = {
    "device-guide": ("办公设备使用指南", "device-guide.txt", "办公设备的日常使用和登记规范。"),
    "meeting-policy": ("会议室预约规范", "meeting-policy.txt", "会议室预约与临时变更说明。"),
    "migration-record": ("历史客户端迁移记录", "migration-record.txt", "用于核对旧版文档迁移批次的公开记录。"),
}


@app.get("/health")
def health():
    return jsonify(status="ok", challenge="core-c01")


@app.get("/")
def index():
    return layout("历史文档预览中心", """
      <p>旧版办公文档已迁移至统一预览平台，员工可以查看公开资料和迁移说明。</p>
      <div class='panel'>授权测试范围：仅检查当前实例中的文档预览功能。</div>
      <ul><li><a href='/documents'>浏览公开文档</a></li><li><a href='/migration-notes'>查看迁移说明</a></li></ul>
    """)


@app.get("/documents")
def documents():
    event("document_list_viewed")
    items = "".join(f"<li><a href='/documents/{doc_id}'>{html.escape(title)}</a>：{html.escape(summary)}</li>" for doc_id, (title, _, summary) in DOCUMENTS.items())
    return layout("公开文档列表", f"<p>以下文档均可在线预览。</p><ul>{items}</ul>")


@app.get("/documents/<document_id>")
def document_detail(document_id: str):
    item = DOCUMENTS.get(document_id)
    if item is None:
        return "文档不存在", 404
    title, filename, summary = item
    preview_href = f"/preview?path=public%2F{filename}"
    return layout(title, f"<p>{html.escape(summary)}</p><p><a href='{preview_href}'>打开在线预览</a></p>")


@app.get("/migration-notes")
def migration_notes():
    event("migration_notes_viewed")
    return layout("历史迁移说明", """
      <p>部分旧版移动客户端曾对附件路径执行额外编码。</p>
      <p>为保证历史链接仍可使用，预览服务会在接收请求后统一规范化旧格式。</p>
      <p>如需核对归档批次，请先浏览公开文档中的迁移记录。</p>
    """)


@app.get("/preview")
def preview():
    raw_path = request.args.get("path", "")
    raw_query = request.query_string.decode("ascii", "ignore").lower()
    wire_query = str(request.environ.get("RAW_URI", request.environ.get("REQUEST_URI", ""))).lower()
    if not raw_path:
        event("root_boundary_violation_rejected")
        return "预览路径无效", 400
    if "../" in raw_path or "\\" in raw_path:
        encoded = any(marker in raw_query or marker in wire_query for marker in ("%2e", "%5c", "%25"))
        event("encoded_traversal_rejected" if encoded else "plain_traversal_rejected")
        if not encoded:
            # Some HTTP clients normalize one encoded traversal before it
            # reaches Flask, so retain the compatibility rejection evidence.
            event("encoded_traversal_rejected")
        return "预览路径无效", 403
    if not raw_path.startswith("public/"):
        event("root_boundary_violation_rejected")
        return "预览路径无效", 403

    normalized_path = unquote(raw_path)
    if normalized_path != raw_path:
        event("compatibility_normalization_used")
    resolved_path = (DATA_ROOT / normalized_path).resolve()
    try:
        resolved_path.relative_to(DATA_ROOT)
    except ValueError:
        event("root_boundary_violation_rejected")
        return "预览路径无效", 403
    if not resolved_path.is_file():
        return "文档不存在", 404
    if resolved_path.parent == PRIVATE_ROOT:
        event("private_archive_accessed")
    elif resolved_path.name == "migration-record.txt" or resolved_path.name == "manifest.json":
        event("archive_manifest_viewed")
        event("normal_preview_viewed")
    else:
        event("normal_preview_viewed")
    return resolved_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
