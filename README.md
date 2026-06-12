# Ombre Brain

Jarv 的永久记忆系统。FastMCP server（`server.py`）+ 记忆引擎（bucket/decay/embedding/dehydrator）。

- **部署（现行）**：Zeabur，`https://0705.zeabur.app/mcp`，构建走 `zbpack.json`（`pip install -r requirements.txt` + `python server.py`）。**push 到 main 即自动上线**，没把握先别 push。
- **旧线（仅存档）**：`render.yaml`、`docker-compose*.yml`、`Dockerfile` 是早期 Render / 自建 Docker 配置，当前不使用。
- **完整文档**：[docs/ob/](docs/ob/)（README / INTERNALS / BEHAVIOR_SPEC / ENV_VARS / CLAUDE_PROMPT）。
- **维护脚本**：`tools/`（embedding 回填、桶检查、重分类、一次性迁移等）。

> 2026-06-12 拆库：Jarvis 本机后端（App API、心跳等）已迁出至私有仓库 `kamoshika0830-bot/jarvis-backend`（本地 `~/ombre-stable`）。后端与 OB 仅 HTTPS 通信。
