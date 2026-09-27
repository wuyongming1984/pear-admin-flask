# Vue desktop migration ledger

Approved: Vue 3 / TypeScript / Element Plus / Vite; light content and deep green sidebar. New `/pc/`, legacy `/` remains default until acceptance. No production database or schema changes.

## Contract
- Independent project `frontend-desktop`; root owns package/build, App, routing, shared UI, api.ts, style.css and Flask entrypoints.
- Modules export route arrays from `src/modules/<domain>/routes.ts` (Vue Router RouteRecordRaw[]), each with meta.title and meta.menuPath (legacy menu URL for permission mapping).
- API import `import {request, query, allRows} from '../../api'` from module folder. `request<T>(path, options?)` accepts relative `/api/v1` path, returns `{code,data,count,msg}`; methods standard fetch RequestInit; JSON bodies must JSON.stringify. `allRows(path,params?)` fetches all paginated records with cap/duplicate guard.
- UI: Element Plus globally registered. Available root components `PageHeader` props title/description; `AttachmentEditor` v-model array, emits busy boolean; simple CSS classes page, panel, toolbar, actions, form-grid, muted, money.
- Complex modules own their editors/dialogs. Shared request layer reports failures through thrown errors; views catch and show ElMessage. Mutations require submit lock; no automatic retries. Edits preserve original invisible fields and attachment/invoice links. Amount input strings.
- Each module owns its folder, tests and `coverage.md` mapping legacy pages/actions/API/new routes. Do not edit other module folders or package manifest. Do not mutate real database. No legacy iframe embedding.

## Work
- [x] Shell/login/menu/tabs/API and dashboard; public entry compatibility
- [x] Core project/order/payment/supplier/payer + invoice/print workflows
- [x] Material and nursery workflow parity
- [x] System management and portal parity
- [x] Local integration, isolated database browser samples, automated regression and schema comparison (scope below)
- [x] Review and fix confirmed integration defects; retain old default pending complete deployment acceptance

Ruling: repository has no Git metadata; isolated new frontend directory and timestamped file archive replace worktree/commit steps. Existing module code remains intact.

## 页面、操作、接口与权限映射

- [核心业务、发票与打印](../frontend-desktop/src/modules/core/coverage.md)
- [材料与苗圃](../frontend-desktop/src/modules/inventory/coverage.md)
- [系统、备份与供应商门户](../frontend-desktop/src/modules/system/tests/coverage.md)
- 工作空间旧 `/view/analysis/index.html` → `/pc/#/` 和 `/pc/#/analysis`，旧 `/view/console/index.html` → `/pc/#/workspace`。继续读取 dashboard overview/monthly-trend/payment-status/top-suppliers 真实接口。
- `/pc/#/login` 登录，`/pc/#/register` 账号开通说明，`/pc/#/forbidden` 无权限，未知路由显示未找到；未知菜单保留并进入 `/unsupported` 说明页；页面资源加载失败提供手动重新加载。
- 菜单只通过 `/api/v1/menu` 读取；旧 URL 别名统一映射，不改库中地址、不自动增加角色权限。个人资料沿用原来的当前账号访问规则。

## 本地验证记录（2026-09-24）

环境：本机 Flask 5052，使用 `tests/serve_pc_audit.py` 创建的临时 SQLite 副本。测试中未启动该副本的定时备份、迁移或初始化。原数据库以只读连接核对。

- 浏览器登录、30个主页面入口；在1280、1440、1920、800px完成120组页面布局检查，字典页额外等待异步加载后复核。无整页横向溢出，长表格在内部滚动，窄窗口菜单可展开。
- 新建项目1234.56元 → 选择该项目新建订单100.01元，供应商联系人自动带入 → 新建关联付款20.01元。列表、详情和打印金额一致，余额80.00元。新端数据沿用同一后端模型及接口。
- 苗木入库10株、单价12.35元 → 出库1株 → 库存9株。
- 材料策划10.5吨、单价100.01元；复现并修复原生Element Plus表格勾选后清空问题，重新勾选并生成4.5吨入库计划，确认入库后库存4.50吨、库存值450.05元。
- 手工发票100.01元+税13.00元，票面113.01元，买卖方和金额大写正确。
- 系统账号、角色、部门、权限、字典、资料和备份配置页面已打开核对；没有在浏览器中修改账号密码或执行备份邮件操作。
- 自动化覆盖金额字符串、附件保留/失败手动重试/迟到响应、未保存草稿、创建成功重置、缓存页面数据刷新、提交锁、权限与跨账号令牌隔离、授权操作、材料和苗圃批量流程、真实表格勾选、打印字段、发票票面、XLSX读取及公式转义。
- Python后端48项、手机端16项、旧版业务JS3组通过；新版构建与TypeScript检查通过。各模块的单测数量及范围见对应清单；最终整体结果附后。
- SQLite `sqlite_master`全部表/索引定义逐项相同，共24张表。原库项目6、订单18、付款12、付款单位2、发票0未变。所有新增验收记录只存在临时副本。

## 已修复的集成问题

- 多标签页复用组件时误读其他页面路由、保存新建页后再次打开重复旧草稿。
- 跨标签页账号变化时旧草稿串用新令牌；过期恢复缺少真实账号；撤销权限后旧编辑页继续显示。
- 个人中心错误依赖角色菜单授权，以及放开自有资料访问后旧菜单映射丢失。
- 订单/付款附件目录复数不符合原上传约定；发票接口引用不存在的项目名称字段。
- 库存和计划销售数量联动、价格税率联动、缓存出库页库存选择不刷新。
- 表格内联数组导致批量选择立即被清空；全局打印样式影响其他页面；打印操作按钮覆盖顶部导航。

## 尚未完成的外部/发布验收

真实OCR、阿里云OSS、邮件发送、备份恢复、生产HTTPS/上传限制未实测；没有用模拟测试宣称这些服务可用。浏览器样例与自动化覆盖不等同于每一种真实历史数据、每一项批量组合、所有文件选择器或物理打印机都已逐项验收。纸张字段和屏幕票面已核对，物理打印分页需现场确认。尚未连接或修改生产数据库。

因此保留旧版默认 `/`，新版提供 `/pc/` 本地验收。前端没有引用Pear/Layui/jQuery或嵌入旧业务页面；旧资源完整保留用于并行和回退。当前构建存在大型依赖包提示（Element Plus/ECharts），不影响构建通过；上线前可继续拆分缓存块。

## 构建、切换和回退

在 `frontend-desktop/` 执行 `pnpm install --frozen-lockfile`、`pnpm build`；产物只进入 `static/desktop/`。手机端仍在 `frontend/` 独立构建。

全部验收后设置 `DESKTOP_DEFAULT=true` 并重启Flask，`/`重定向新版；设回false并重启即回退。`/legacy/`和原有旧页面路由继续可访问。部署只更新应用代码/静态资源，绝不执行包含删表逻辑的初始化、数据库同步或迁移命令。

最终新版前端：16个测试文件、108项测试通过；`pnpm build`（含TypeScript检查）通过。本地5050服务已重启，`/`、`/legacy/`、`/pc/`、`/m/`均HTTP200，默认入口保持旧版。


补充交叉验证：旧版项目页面已读取并显示新端创建的项目及1234.56元合同金额。材料单项出库1.5吨与确认已实测；保留既有后端规则：普通确认仅迁移出库记录数量/状态，不再次扣现有库存。既有单项接口从计划销售量扣数，计划销售量为0时可产生负值（本地副本中复现）；本次未改变库存算法。上线前应由业务方确认该原有行为是否仍符合当前流程，不应把它当作本次新增的库存算法。
