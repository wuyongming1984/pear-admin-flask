# 本地改写与预览

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-local.ps1
```

- 新版实时开发预览：<http://127.0.0.1:5174/static/desktop/>。修改 `frontend-desktop/src/` 后自动更新。
- 已构建新版：<http://127.0.0.1:5050/pc/>。更新此入口需要在 `frontend-desktop/` 执行 `pnpm build`。
- 旧版：<http://127.0.0.1:5050/legacy/>。
- 手机端：<http://127.0.0.1:5050/m/>。

后端使用 `scripts/run_local.py`，代码修改后自动重启，只监听本机。数据库为现有 `instance/pear_admin.db`，登录使用这个本地库中的原账号。页面提交会修改本地库，改写前可自行备份；启动不会初始化、清空或迁移数据库。

本地运行入口覆盖进程内的数据库设置，禁用 OSS、OCR 凭据和自动备份调度，不修改 `.env`。云端上传、真实 OCR 和邮件备份不属于此环境的验证范围。请使用本启动脚本，直接照旧运行 Flask 可能读取 `.env` 中的远程数据库配置。

服务后台运行，关闭页面不会停止服务。日志和启动 PID 保存在 `instance/local-*.log` 与 `instance/local-*.pid`；重启电脑后需重新执行启动脚本。Python 环境与前端依赖均属于本机运行文件，不需上传仓库。

提交前在本地查看 `git diff`，按实际功能改动运行相关测试、构建。数据库、`.env` 和上传附件应继续留在本机。此次运行不包含仓库推送或云端发布。
