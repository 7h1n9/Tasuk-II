# core-c01 internal

这是独立的历史文档预览应用。过滤在第二次 URL 规范化之前执行，最终路径必须仍位于 /app/data 控制根目录内，因此漏洞只能从公开目录进入本题私有归档。

私有文件名由 VARIANT_SEED 派生，普通重置保留文件名但重新生成 Flag。题目不依赖 challenges/common/advanced_app.py，也不允许读取数据根目录之外的文件。
