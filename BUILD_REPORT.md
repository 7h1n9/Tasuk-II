# Second Stage A Group

## core-a02

- 业务场景：企业采购订单查询系统，包含登录、工作台、我的采购、公告、说明、订单详情和附件下载。
- 漏洞类型：对象级访问控制缺陷（订单详情 API 只校验登录，不校验 owner）。
- 正常流程：首页 → 登录 → 我的采购 → 订单详情 → 物流/附件信息。
- 漏洞触发流程：公告发现跨部门订单号 → 请求订单详情 API → 发现随机附件能力 URL → 下载内部验收报告 → 提取 Flag。
- 动态元素：`VARIANT_SEED` 派生采购订单号；容器启动生成附件 token；`INSTANCE_FLAG` 只在附件报告中出现。
- 验证结果：Docker build PASS；health PASS；内部 solver PASS；错误/正确提交 PASS；reset 后旧 Flag 失效、新 Flag 生效、订单号变化 PASS。

## core-a03

- 业务场景：企业内部项目审批门户，包含 employee 登录、项目中心、审批中心、个人设置、帮助和管理审阅页面。
- 漏洞类型：客户端可控门户上下文导致角色边界错误。
- 正常流程：首页 → employee 登录 → 项目中心 → 审批中心 → 工作空间设置 → 普通审批队列。
- 漏洞触发流程：观察正常审批请求 → 切换工作空间生成 unsigned `portal_state` → 修改已有上下文中的 persona → 访问管理审阅页 → 下载内部项目归档 → 提取 Flag。
- 动态元素：`VARIANT_SEED` 派生项目编号；管理归档 token 每次容器启动变化；Flag 来自 `INSTANCE_FLAG`。
- 验证结果：Docker build PASS；health PASS；内部 solver PASS；普通/特权角色响应差异、错误/正确提交、reset 和 variant PASS。

## core-a04

- 业务场景：企业邮件模板预览系统，包含登录、模板中心、创建模板、模板详情、变量说明、个人资料和预览 API。
- 漏洞类型：真实 Jinja2 模板渲染器的服务器端上下文信息泄露。
- 正常流程：首页 → employee 登录 → 模板中心 → 创建/选择模板 → 正常变量预览 → 查看变量说明。
- 漏洞触发流程：提交未知变量观察 StrictUndefined 错误 → 发现额外 context root → 读取应用配置对象的通知字段 → 获得 Flag。
- 动态元素：`VARIANT_SEED` 派生模板编号和员工别名；配置字段内容来自 `INSTANCE_FLAG`；没有名为 `flag` 的模板变量或字符串 contains 模拟判断。
- 验证结果：Docker build PASS；health PASS；内部 solver PASS；模板正常渲染、错误差异、配置读取、错误/正确提交、reset 和 variant PASS。

## core-a05

- 业务场景：企业合同审核平台，包含 submitter 登录、合同中心、提交合同、活动记录、状态查询和审核结果 API。
- 漏洞类型：业务流程权限绕过（审核结果 API 检查 approved 状态但不检查 reviewer 角色）。
- 正常流程：首页 → submitter 登录 → 提交普通合同 → 合同详情 → 查看状态 → 活动记录。
- 漏洞触发流程：观察状态/审核请求 → 从活动记录发现另一份 approved 合同 → 请求审核结果 → 发现最终附件 → 下载附件 → 提取 Flag。
- 动态元素：`VARIANT_SEED` 派生普通/内部合同编号；最终附件 token 每次容器启动变化；Flag 来自 `INSTANCE_FLAG`。
- 验证结果：Docker build PASS；health PASS；内部 solver PASS；错误/正确提交、reset 和 variant PASS。

## Summary

- Build: PASS — each new challenge built from its own directory-local Dockerfile, and the backend image rebuilt with the updated registry.
- Health: PASS — all five challenges returned HTTP 200 from `/health` during the full regression.
- Solver: PASS — all five internal solvers dynamically discovered business identifiers/capability paths and completed the intended chain.
- Flag Verification: PASS — wrong submissions returned `correct=false`; discovered flags returned `correct=true`.
- Reset: PASS — each reset rotated the instance Flag; the old Flag was rejected and the new solver result was accepted.
- Variant: PASS — `regenerate_variant=true` changed a business identifier for all five challenges while the solver remained effective.
- Public Metadata: PASS — registry API listed all five as non-legacy and did not expose internal metadata fields.
- Challenge Isolation: PASS — new challenge images use `USER 10001`, no privileged mode, no host network, no Docker socket, and no host mounts; target Dockerfiles do not copy `challenges/common/advanced_app.py`.
- Security Isolation: FAIL / LIMITATION — the requested no-external-network property for core-a04 was not enforceable with the current Docker Desktop port-publishing contract. Docker `internal: true` and `network: none` both made the locally published challenge port unreachable; normal bridge networks preserve the required local HTTP target but do not prove outbound egress is blocked. The failed isolation experiment was reverted and recorded in task state; no public target was contacted.

## Full Regression Evidence

The local backend at `http://127.0.0.1:18081` completed:

`create instance → health → normal home → wrong submit → solve/submit → reset with regenerated variant → health → stale Flag rejection → solve/submit again → destroy`

for `core-a01`, `core-a02`, `core-a03`, `core-a04`, and `core-a05`.

The backend environment reports instance URLs using `192.168.236.1` and a port offset, but that VMNet proxy was unavailable in this Windows session. Validation therefore used the same instance `host_port` through `127.0.0.1`; the Docker containers and backend lifecycle were the real local targets.
