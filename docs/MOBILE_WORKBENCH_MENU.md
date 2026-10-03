# 移动端工作台菜单

菜单地址为 `/m/`，类型为「路由」，打开方式为「新窗口」(`_blank`)。电脑端从菜单打开独立手机端，手机端中的同名入口返回首页。

旧菜单地址为空时，前端仅为「移动端工作台」提供兼容入口。其他未配置菜单仍显示菜单说明，不改变业务访问权限。

已有数据库可运行以下配置命令。脚本先备份菜单与角色关系，再修正该菜单的地址、类型和打开方式；已有菜单的 ID、上级、启用状态和授权保持原值。菜单不存在时，在「工作空间」下创建入口，沿用已拥有工作空间或工作台菜单的角色，不授予其他业务模块权限。重复运行不会新增重复菜单或授权。

```powershell
.venv\Scripts\python.exe scripts/configure_mobile_workbench.py --sqlite instance/pear_admin.db
```

部署时，在使用同一份生产 `.env` 的应用容器内运行：

```bash
python scripts/configure_mobile_workbench.py --config prod
```

备份默认保存在 `instance/mobile-menu-backups/`。脚本不启动 Flask、调度器或云服务。本地验证不代表服务器已更新。
