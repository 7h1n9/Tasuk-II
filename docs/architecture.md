# 架构说明

第一阶段采用三层结构：

- 控制服务：FastAPI + SQLAlchemy + MySQL
- 管理界面：React + Vite + TypeScript
- 题目容器：独立 Docker 镜像 + 动态 Flag + 健康检查

