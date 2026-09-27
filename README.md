# Pear Admin Flask

工程项目、供应商、订单付款、材料与苗圃管理系统。后端采用 Flask / SQLAlchemy，前端采用 Layui / Pear Admin。

## 本地启动（当前已配置环境）

在项目根目录运行 PowerShell：

```powershell
.\.venv\Scripts\python.exe -m flask --app pear_admin run --host 127.0.0.1 --port 5050 --no-reload --no-debugger
```

访问 http://127.0.0.1:5050 。当前本地数据库为 `instance/pear_admin.db`，保留此前创建的账号和 44 条临时业务数据。

新机器依赖：Python 3.10 以上，按 `pyproject.toml` 和 `poetry.lock` 使用 Poetry 安装。JWT 依赖版本应遵循锁文件，避免现有整数用户标识与新版本不兼容。

**不要对现有数据库执行 `flask init`**：旧初始化命令包含删表重建逻辑。当前文档中的启动命令不会初始化或重置数据。全新数据库引导仍需单独处理，不应直接套用现有数据环境的部署脚本。

## 配置

配置入口为 `configs.py`，通过 `.env` 或环境变量提供配置。开发环境默认 SQLite，配置非本地 `MYSQL_HOST` 时切换 MySQL；生产配置使用 MySQL。

- `SECRET_KEY`：应用签名密钥。
- `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE`：数据库配置。
- `ALIYUN_ACCESS_KEY_ID` / `ALIYUN_ACCESS_KEY_SECRET` / `ALIYUN_OSS_BUCKET_NAME` / `ALIYUN_OSS_ENDPOINT`：OSS 配置。
- `BAIDU_OCR_API_KEY` / `BAIDU_OCR_SECRET_KEY`：发票识别配置；未配置时识别明确失败，不生成模拟发票。普通发票上传可继续保存文件，并记录识别失败原因。

## 目录与维护

详见 [项目结构与清理说明](docs/PROJECT_STRUCTURE.md) 和 [保留脚本说明](scripts/README.md)。

- `pear_admin/`：应用工厂、接口、模型、页面路由及扩展。
- `templates/`、`static/`：页面和静态资源。
- `data/`：菜单、权限和字典数据。
- `migrations/`：正式数据库迁移。
- `scripts/`：仍需维护的备份、系统数据导入导出及结构同步工具。
- `instance/`、`uploads/`、`static/uploads/`：本地运行数据与附件。

## 部署参考

保留现有 [DEPLOY.md](DEPLOY.md)、[阿里云部署步骤](阿里云部署步骤.md)、Dockerfile、docker-compose.yml、nginx 及部署脚本。它们包含环境相关设置及数据库初始化/同步操作，本次仅检查文件依赖，未运行或验证云端部署。

历史排查、一次性迁移、测试脚本和调试产物已移出项目，恢复位置和清单见项目结构说明。

旧 `deploy_to_aliyun.ps1` 导入流程缺少两项原始依赖，所需历史 SQL 已归档；使用前请阅读项目结构说明中的“历史部署边界”。


## 新版电脑端（本地并行验收）

- 新版入口：`http://127.0.0.1:5050/pc/`，Vue 3 + TypeScript + Element Plus。
- 旧版默认入口 `/`，保留 `/legacy/`；手机端 `/m/` 保持独立。
- 桌面源码 `frontend-desktop/`，构建资源 `static/desktop/`。
- 在 `frontend-desktop` 运行 `pnpm install --frozen-lockfile`、`pnpm build`；后端仍使用原有 Flask 启动方式。开发调试可运行 `pnpm dev`，API 转发到本机5050。
- 本地验证：`pnpm test`；后端 `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"`；手机端在 `frontend/` 运行 `pnpm test`。
- 完整验收前不切换默认入口。验收通过后通过环境配置 `DESKTOP_DEFAULT=true` 并重启应用切换 `/`；设回 `false` 即回退，不修改菜单和数据库。
- 页面/操作映射、验证范围与未验证外部服务见 [迁移验收记录](docs/DESKTOP_MIGRATION.md)。不要为部署新版运行初始化、删表、数据库同步或自动迁移脚本。
