# 项目清理实施计划

> **For agentic workers:** Use superpowers:executing-plans for inline implementation. Steps use checkbox syntax.

**Goal:** 梳理现有项目，移除不参与当前运行的历史、测试和调试代码。
**Architecture:** 保留 Flask API、ORM、视图、模板和迁移边界；清理文件先归档并校验 SHA256。数据库与上传文件不变。
**Tech Stack:** Python / Flask / SQLAlchemy / SQLite / Layui / Docker。
**Spec:** 用户要求“梳理这个项目，去除冗余和测试代码”。

## Global Constraints
- 保留当前 44 条测试业务记录；本次清理代码而非业务数据。
- 不执行历史迁移、远程同步、云上传或部署命令。
- 保留被应用及部署链路引用的脚本，保留第三方静态资源和正式迁移。
- 无 Git 元数据，使用外部归档、原始文件副本和清单代替提交及 worktree。

## Review Focus
- 备份调度依赖 scripts/backup_db.py，必须保留。
- server_update.sh 依赖 import_data.py 和 update_db_schema.py，必须保留。
- OCR 未配置时不能生成随机发票；已配置时必须仍选用真实 OCR。
- 原始异常不能被写入不存在的硬编码日志路径掩盖。
- 模板、菜单、业务列表和当前数据必须保持可用。

### Task 1: 归档与目录清理
- [x] 保存项目外清单及修改前副本，保存 SQLite 一致性备份。
- [x] 对清单内逐个文件 Move-Item，验证根路径、目标目录和内容哈希。
- [x] 保留 scripts 下 backup_db.py、import_data.py、export_data.py、update_db_schema.py、两个备份调度安装脚本。

### Task 2: 移除运行代码中的测试残留
- [x] 在项目外运行 OCR 配置缺失检查，先确认现有代码会使用默认凭据。
- [x] 删除 MockOCR 和硬编码默认凭据；真实 OCR 在缺少配置时给出明确错误，上传流程仍能捕获识别失败。
- [x] 删除重复 OCR 方法和重复 JWT 配置，删除临时日志文件写入、供应商调试 print。
- [x] 菜单异常使用 Flask logger.exception 后重新抛出原异常。
- [x] 更新 .gitignore、.dockerignore、README 和项目结构说明。

### Task 3: 验证
- [x] 语法编译所有生产 Python；比对清理前后路由映射及数据库内容。
- [x] 本地无网络 OCR 检查：未配置明确失败，已配置使用 BaiduOCR；模拟上传验证无凭据仍可上传。
- [x] 使用独立进程加载新代码，验证登录、菜单非空及所有业务列表。
- [x] 重启本次启动的本地服务，验证浏览器菜单与项目数据。
- [x] 独立复核清理清单和运行依赖，将结果写入项目说明。

## 实施记录
- 无 Git 仓库，使用外部原始副本及 SHA256 清单提供恢复能力；未创建提交或工作树。
- 一次性验证脚本与日志存放于外部归档，业务目录不新增测试脚本。
- 额外发现并修复系统导出列位置错误：临时文件复现失败后，改用具名列映射，往返验证通过。
- 独立复核指出旧 PowerShell 导入流程引用已归档 SQL；保留历史脚本并在 README 和结构说明记录其原有缺失依赖及恢复要求。
- 所有验证通过，服务已重启并用浏览器确认侧栏、首页统计正常。
