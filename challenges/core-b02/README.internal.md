# core-b02 internal

这是独立的资产保修核验应用，漏洞仅存在于 department 的旧版查询拼接路径。
asset_no 使用参数化查询，接口只返回布尔结果；Flag 存在于 SQLite 的配置记录中，必须通过元数据与真假响应完成推断。

题目不依赖 challenges/common/advanced_app.py。实例的 VARIANT_SEED 决定数据库中的稳定业务对象，普通重置保留该种子，Flag 由控制端单独轮换。
