# 税务发票批次导入

`scripts/import_tax_invoices.py` 将预先校验的税务 Excel 记录及商品明细导入现有发票库。默认只查重预览，只有显式指定 `--import` 才写入。

本次数据包是 `scripts/invoice_batches/20261004.fernet`，包含 1,967 张发票和 2,934 行明细。公开仓库只保存 Fernet 加密的数据包；解密密钥另行提供，不能提交到仓库。脚本在内存中解密，服务器无需上传 Excel，也无需安装新依赖。

## 服务器执行

先拉取代码：

```bash
cd /root/pear-admin-flask && git pull --ff-only origin main
git log -1 --oneline
```

在正在运行的应用容器内查重预览。出现密钥提示后输入单独提供的密钥，输入不会回显：

```bash
docker exec -it -w /app pear_admin_web python scripts/import_tax_invoices.py --preview
```

核对预览结果后，执行正式导入：

```bash
docker exec -it -w /app pear_admin_web python scripts/import_tax_invoices.py --import
```

也可通过 `--key-file /app/instance/invoice-import.key` 指定受保护的密钥文件。密钥文件必须保存在 Git 忽略的 `instance/` 或仓库外，Linux 权限设置为 `600`。数据包解密失败时不会初始化数据库连接。

现有 Compose 配置将项目目录挂载到容器 `/app`，单独运行本脚本无需重新构建或重启应用。若部署方式不同、容器内看不到新脚本，可先 `docker cp scripts/import_tax_invoices.py pear_admin_web:/app/scripts/import_tax_invoices.py` 并复制 `scripts/invoice_batches/` 到容器 `/app/scripts/invoice_batches/`。

## 重叠数据处理

- 数电发票按完整的 20 位票号匹配；传统发票按发票代码和号码匹配。
- 已有记录保留原文件、项目、供应商、分类、明细及付款关联。名称、税号、日期或金额的差异写入核对报告，不自动覆盖。
- 历史记录缺失发票代码、或匹配多个记录时保守跳过并标记人工核对。
- 新发票同时导入商品明细、负数金额、原始红冲状态及特殊业务信息；不自动分配项目或付款单。
- 正式导入重新查重。重复执行应新增零张，实际数量以执行时的数据库为准。

本次此前的线上快照是 171 张发票，预计跳过 139 张、新增 1,828 张及 2,681 行明细，导入后共 1,999 张。重叠记录中有 3 张存在名称或税号差异。上述数字只作核对参考，预览会重新查询正式数据库。

## 事务与核验

正式环境要求相关表使用 MySQL InnoDB。脚本使用可串行化事务、行锁及间隙锁，将导入、金额和明细核验放在一次事务内，失败即回滚；导入期间可能短暂阻塞发票编辑。正式执行前会校验数据包里的线上基线 ID 和票号，目标不符即停止。

预览和导入报告保存在 `instance/invoice-tax-import-20261004/audit/<时间戳>/`：

- `preview.json`：只查重的数量、金额及警告。
- `skipped-existing.json`：跳过记录和差异。
- `before-backup.json`：正式导入前的发票、明细、付款关联表快照。
- `verified-before-commit.json`：事务内核验结果，尚未提交。
- `result.json`：事务提交成功后的结果，`committed: true`。

报告和备份包含业务数据，仅存服务器本地，不应上传公开仓库。脚本只初始化数据库，不启动应用的 OCR、OSS 或调度任务。

本地回归测试使用合成数据和隔离 SQLite；执行命令：

```bash
python -m unittest tests.test_tax_invoice_batch_import -v
```

本地测试验证加密包解密和篡改拒绝、预览不写入、原记录与关联保留、金额异常回滚及重复导入新增零张。实际 MySQL 导入完成应以服务器的 `result.json` 为准。
