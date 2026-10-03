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

服务器：在配置及依赖已就绪的新版本代码目录执行。缺少字段时自动备份付款表，再增加缺失字段：

```sh
python scripts/migrate_payment_audit.py --config prod
```

备份保存在服务器项目的 `instance/payment-audit-backups/ums_pay.payment-audit-*.sql`，使用容器内的 `mariadb-dump` / `mysqldump`，包含付款表原结构和数据。目录由 `/app` 挂载保留在宿主机；备份文件仅当前用户可读写。字段已经齐全时直接跳过，可重复执行。历史创建人及时间保持 NULL。

## 订单、付款及手机最近订单同时报错

新版 `PayORM` 会查询这 8 个字段。订单列表预加载关联付款，手机最近订单使用相同后端，因此旧版 `ums_pay` 缺字段时三个入口都会失败（例如 `Unknown column 'ums_pay.generated_at'`）。

阿里云更新命令：

```sh
cd /root/pear-admin-flask && git pull --ff-only origin main && bash server_update.sh
```

`server_update.sh` 构建 web 镜像后，先运行上述备份及迁移，再使用服务器数据库只读检查 `/workspace/orders`、`/workspace/payments`、`/order/`、`/pay/`。备份、迁移或任一接口检查失败都会停止更新。全部通过后才更新 web 容器。检查输出只含状态、数量和查询耗时，不输出业务记录或凭据。

接口检查是在同环境的一次性容器内执行，未经过线上 Nginx/Gunicorn。更新后仍须刷新订单页、付款页及手机首页，并检查 `docker logs --tail 80 pear_admin_web`。
