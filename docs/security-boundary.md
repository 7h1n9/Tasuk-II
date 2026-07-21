# 安全边界

- 题目容器不得使用 `--privileged`
- 题目容器不得挂载宿主机目录或 Docker Socket
- 题目容器必须运行在非 root 用户下
- 题目实例使用独立网络

