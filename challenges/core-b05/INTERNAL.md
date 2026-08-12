# core-b05 内部说明

## Scenario

这是一个员工资料与文件处理中心。演示员工可以上传无害文本文件、查看处理状态、
预览生成的副本并下载自己的文件。

## Intended discovery chain

1. 使用 `employee` / `employee-pass` 登录。
2. 访问员工资料、上传文件和我的文件页面。
3. 上传普通文本文件，观察上传响应和我的文件列表中的处理详情入口。
4. 我的文件页面还包含另一份内部复核文件的审核动态编号。查询该编号的处理详情
   会返回预览能力，并暴露不同的文件所有者。
5. 预览处理器接受生成的预览令牌，却没有执行下载处理器中的所有者校验。内部
   复核预览中包含动态的 `INSTANCE_FLAG`。

## Vulnerability boundary

预期问题是文件处理流程的业务隔离缺失：已登录员工可以获取并打开另一名员工的
复核预览。上传文本会被转义，绝不会执行。本题不用于演示命令执行、路径穿越、
SQL 注入或任意代码执行。

## Dynamic behavior

- `INSTANCE_FLAG` 控制内部复核预览中的 Flag 文本。
- `VARIANT_SEED` 会改变生成的文件编号。
- 预览令牌和会话令牌在运行时生成。
- `tests/solve.py` 从页面和 API 响应中发现文件编号及预览地址。

## Events

应用会记录 `login_success`、`file_uploaded`、`file_processing_view`、
`file_preview` 和 `file_download` 事件，并附带实例标识。
