# ctf-agent-range

用于 `CTF Web 自动化 Agent` 的第一阶段本地靶场系统。

## 目标

- 本地授权环境内运行
- 后端控制服务负责题目、实例、Flag、运行记录管理
- 前端管理界面负责题目列表、实例管理、运行记录和统计
- 每个题目为独立容器，支持动态 Flag、重置和销毁

## 启动

### Windows PowerShell

```powershell
.\scripts\init.ps1
.\scripts\start.ps1
```

### Kali / Ubuntu

```bash
chmod +x scripts/*.sh
./scripts/init.sh
./scripts/start.sh
```

## 访问地址

- 前端：`http://localhost:3000`
- 后端：`http://localhost:18080`
- API 文档：`http://localhost:18080/docs`

## 端口说明

- 宿主机 `8000` 在当前环境已有其他服务占用，因此后端控制服务改用 `18080`
- 题目实例端口由后端随机分配，落在 `18000-18999` 区间，并自动避开 `18080`
- MySQL 只保留在 Compose 内部网络，不对宿主机暴露端口
