# 保留脚本

| 文件 | 用途及调用关系 |
| --- | --- |
| backup_db.py | 数据备份及邮件发送；被系统备份接口和 APScheduler 调用 |
| import_data.py | 同步菜单、角色、权限、字典；被 server_update.sh 调用，默认生产配置，会写数据库 |
| export_data.py | 从开发环境导出系统配置到 data/system_data.json；按字段名读取角色权限 |
| update_db_schema.py | 依据 ORM 同步数据库结构；部署更新文档及 server_update.sh 使用 |
| setup_scheduler.ps1 | Windows 定时备份安装器；保留原始环境路径，运行前需按机器调整 |
| setup_aliyun_cron.sh | 云服务器定时备份安装器；保留原始容器及目录设置，运行前核对 |

这些脚本不是应用启动前必须全部执行的步骤。导入、结构同步、备份发送和调度安装均有副作用。本次清理没有执行这些操作，仅对导出脚本使用临时输出文件验证。

其他旧脚本已归档到项目外，参见 docs/PROJECT_STRUCTURE.md。
