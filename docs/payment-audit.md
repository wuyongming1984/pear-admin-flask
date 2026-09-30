# 付款审批单经办人及后台留痕

- 新增及经办人为空的旧单据编辑页，默认使用当前登录昵称（昵称为空时使用登录名）；仍可手工修改。已填写的经办人不覆盖。
- 保存时后端独立记录 `generated_at`、`created_by_id/username/nickname`，不接受客户端覆盖。
- `updated_at`、`updated_by_id/username/nickname` 保存最后一次成功修改信息。账号和昵称保存当时快照，账号改名不会改变旧记录。
- `handler` 是单据上的经办人，可以与登录操作人不同。`create_at` 保持原有单据日期语义。
- 历史单据无法追溯的生成时间、创建人保持 NULL，不以迁移时间或本次编辑人补造。
- 当前保存创建及最后修改信息，不提供完整历次修改日志。

## 数据库升级

必须先增加字段，再运行新版后端。迁移仅增加 8 个可空字段，可重复执行。

本地（自动备份原 SQLite）：

```powershell
python scripts/migrate_payment_audit.py --sqlite instance/pear_admin.db
```

服务器：先备份数据库；在配置及依赖已就绪的新版本代码目录执行：

```sh
python scripts/migrate_payment_audit.py --config prod
```

本次未执行服务器迁移或部署。`server_update.sh` 本身不会自动执行该迁移。
