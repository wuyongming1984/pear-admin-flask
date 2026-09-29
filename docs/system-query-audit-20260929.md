# 系统数据库查询审计（2026-09-29）

## 结论与边界

确认 10 个读取接口存在随记录数增长的重复查询，本次已在本地代码中修复。
主要原因是循环内统计、ORM 序列化时逐条加载关联对象，以及逐单查询明细。
这些问题会增加数据库往返次数；应用与数据库跨网络部署时尤其值得优先处理。
不能根据本地 SQL 次数直接推断生产响应时间或加速倍数。

基线为提交 `6859ceb`，测试使用隔离 SQLite 内存数据库、合成数据，并禁止网络连接。
每次请求前清除 SQLAlchemy session，避免缓存关联对象掩盖问题。
统计包含请求中的认证、分页 count、关联加载，排除建表和造数。
本次未连接生产数据库，未发布或部署；MySQL 执行计划、慢查询、锁等待及容器排队尚未验证。

## 已实测和修复

| 接口（通常有 `/api/v1` 前缀） | 合成样本 | 修改前 SQL | 修改后 SQL | 改动 |
| --- | --- | ---: | ---: | --- |
| `/project/` | 20 个项目及附件 | 23 | 4 | 批量预加载附件，保留 slim 模式 |
| `/order/` | 40 个订单，其中 20 个无付款且供应商不同 | 27 | 7 | 补充订单供应商预加载 |
| `/pay/` | 20 条付款，不同订单、项目、付款单位、收款单位及发票 | 103 | 4 | 关联对象预加载，发票批量查询 |
| `/material/options` | 20 个有数据项目 + 1 个空项目 | 107 | 7 | 五类数量改为分组统计 |
| `/material/planning` | 20 条材料策划 | 62 | 3 | 项目及供应商预加载，待入库数量按页批量统计 |
| `/material/inbound?status=pending` | 20 条待入库记录 | 62 | 2 | 预加载项目、供应商、发票 |
| `/material/inventory` | 20 条库存 | 82 | 2 | 预加载项目、供应商、销售商、入库发票 |
| `/material/outbound` | 20 条待出库记录 | 82 | 2 | 复用库存 join，并加载关联信息 |
| `/nursery/orders` | 20 个出库单，每单 2 条明细 | 21 | 2 | 汇总后批量查询明细，保持数据库单号匹配规则 |
| `/portal/reconcile/<token>/data`（无 API 前缀） | 20 条未关联订单的付款 | 24 | 4 | 预加载付款单位与收款单位 |

材料出库的基础样本中出库发票和入库发票相同；另用不同/缺失出库发票、快照销售商测试，确认仍为 2 次查询。
补充 100 组数据测试，分页上限 100，以上分页接口、材料选项和苗圃单据仍满足同一查询预算。
这里的上限仅适用于本次样本和分页范围；`selectinload` 在更大数据集上可能分批执行，不能理解为任意数据量永远固定次数。

保留并验证的行为包括：金额、关联名称、发票列表、待入库与已完成状态区分、
空项目/空关联、NULL 与空字符串规格的差异、重复策划键、分页/项目筛选、
出库快照的零数量与零价格、孤立出库记录排除、对账 token 的数据范围。
没有修改写入流程或表结构。

## 其他检查结果

以 1 组和 20 组项目、订单及付款数据分别测量：

| 接口 | 两种样本下 SQL 次数 | 结论 |
| --- | ---: | --- |
| `/workspace/orders` | 11 / 11 | 已批量预加载，未见按行增长 |
| `/workspace/payments` | 12 / 12 | 同上；固定往返仍有进一步合并空间 |
| `/dashboard/overview` | 7 / 7 | 固定统计查询 |
| `/dashboard/payment-status` | 2 / 2 | 分组统计 |
| `/dashboard/monthly-trend` | 3 / 3 | 分组统计 |
| `/dashboard/top-suppliers` | 2 / 2 | 分组统计 |
| `/material/invoice` | 3 / 3 | 已批量加载关联及明细 |
| `/material/dashboard/stats` | 3 / 3 | 次数固定，但存在全量读取问题，见下文 |
| `/nursery/dashboard/stats` | 7 / 7 | 固定统计查询 |

用户及角色列表在单用户/单角色样本中分别为 3 次；代码序列化仅使用本表字段。
没有将这两个样本误当作多用户规模测试。

## 仍需关注的性能问题

以下为代码检查发现的后续优化项，本次未对生产数据测量，也未修改其业务行为：

1. **材料、苗圃页面拉取全量数据后在前端分页。**
   `frontend-desktop/src/modules/inventory/Material.vue` 的 `load()` 使用 `allRows()`，
   `Nursery.vue` 的台账/流水也类似；苗圃 `/orders` 仍返回完整历史和全部明细。
   即使单页 SQL 减少，总请求数、响应体和浏览器处理量仍会随数据增长。
   建议将筛选、排序、分页一起移到服务器，保留专门的全量导出流程；这涉及交互行为，需要单独实现及验证。
2. **材料看板读取全部库存对象后在 Python 中求和。**
   `pear_admin/apis/material.py::dashboard_stats` 可改用数据库 `SUM(total_value)`。
   当前查询次数并不多，但读取行数和 Python 内存随库存增长。
3. **部分批量操作仍逐条查库。**
   材料 `inventory/batch_calculate` 对每条库存单独汇总待出库量；
   `planning/generate_inbound`、`outbound/batch` 等存在逐条读取记录。
   这会影响大批量保存/处理，后续应批量取数并验证同一库存重复出现、事务回滚及数量扣减规则。
4. **索引与单条查询成本未做生产验证。**
   材料策划的批量待入库汇总涉及项目、材料名称、规格、状态；
   应先在服务器检查 `EXPLAIN`、已有索引及真实数据分布，再决定复合索引。
   合并查询降低往返次数，并不保证所有查询都能使用合适的索引。

## 验证与复现

新增回归文件：`tests/test_system_query_efficiency.py`。
完整后端回归 132 项全部通过（58.223 秒），`git diff --check` 通过。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest tests.test_system_query_efficiency -q
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p 'test_*.py' -q
```

本地完整测试日志：`output/system-query-tests.log`。
其他接口测量结果：`output/system-query-other-endpoints.jsonl`（仅计数、耗时及响应大小，无业务内容）。

服务器代码包含本次修改后，可在现有 web 容器内执行：

```bash
docker exec -w /app pear_admin_web python scripts/profile_editor_queries.py --config prod --scope system
```

新增 `--scope system` 检查普通项目/订单/付款列表、新工作台、材料列表及看板。
分页接口仅取首页 20 条；材料选项及统计接口仍计算其正常业务范围。
刻意不默认运行返回全历史的苗圃订单接口，也不要求输入或输出对账 token。
脚本仅执行进程内 GET，并阻止非 SELECT SQL；不启动调度器、不迁移数据库、不调用写入接口。
输出 `sql_count`、`sql_ms`、`elapsed_ms`、`response_bytes`，不输出记录正文或凭据。
测量不包含浏览器、网络、Nginx、Gunicorn 等待；SQL 执行计时也不代表全部 ORM 取数和序列化成本。
