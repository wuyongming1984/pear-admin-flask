# 付款回单库

“订单付款管理”菜单中，付款回单库位于发票库下方。

上传 PDF、PNG、JPG 或 WebP 回单，支持拖入和多选，每份不超过 20 MB。
同一文件重复上传会返回原回单，不覆盖信息或付款关联。上传后可填写银行流水号、
付款日期、付款单位、收款单位、金额、银行和备注，并在页面内预览原文件。

点击“关联付款单”，按付款编号、单位或项目查找，勾选后保存。一份回单可关联
多张付款单，一张付款单也可关联多份回单。名称相近仅作提示，不自动建立关联。
已有关联保留，可逐条解除；删除回单记录会解除其关联，保留付款单和原文件。
付款单详情和编辑页面均可点击回单返回库中查看。

## 数据迁移

本地指定 SQLite：

```powershell
python scripts/migrate_payment_receipts.py --sqlite instance/pear_admin.db
```

服务器更新脚本 `server_update.sh` 已包含迁移步骤；更新发布时会创建两张新表，
把菜单插在发票库下方，并继承发票库现有的角色授权。
迁移可重复执行，不修改已有付款单字段。变更前保存菜单及授权 JSON 快照，
SQLite 同时保存完整数据库备份，位于 `instance/receipt-migration-backups/`。

## 本次本地预览

源码位于 `D:\pear_admin\payment-receipts`，分支 `codex/payment-receipts`。
预览入口：`http://127.0.0.1:5052/pc/#/payment-receipts`。
预览使用独立的数据库副本和本地文件存储，未连接云端数据库、OSS、OCR 或任务调度器。
菜单和关联功能已使用示例回单验证；发布后的 MySQL、OSS 和生产环境尚需部署验证。
