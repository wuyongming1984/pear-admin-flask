# Material and nursery desktop operation coverage

Native Vue 3 + Element Plus, using the existing authenticated JSON API. No iframe, legacy template rendering, database change or production mutation was used. Routes below are relative to `/pc/#`.

## Material

| Legacy page / action | New route / action | API |
| --- | --- | --- |
| dashboard | `/material/dashboard`, valuation / pending counts and navigation | GET `/material/dashboard/stats` |
| planning list, project / remainder filter, search | `/material/planning`, all-page retrieval, client pagination and search | GET `/material/planning`, `/material/options` |
| planning_add | Native dialog; remaining quantity initialized to total; numeric strings preserved | POST `/material/planning` |
| Excel planning import and template | Project selector, `.xls/.xlsx` input, original template download | POST multipart `/material/planning/import` |
| generate inbound | Selected plans with individually editable quantities | POST `/material/planning/generate_inbound` |
| planning supplier / single and batch delete | Batch supplier, row delete, batch delete | PUT `/material/planning/batch_supplier`, DELETE `/material/planning/:id`, `/material/planning/batch` |
| inbound / inbound_add / inbound_edit | `/material/inbound`, pending/completed filter, native add/edit dialog preserving other fields | GET/POST `/material/inbound`, PUT `/material/inbound/:id` |
| inbound batch number | Native batch-number dialog | PUT `/material/inbound/:id/batch` |
| inbound invoice link / unlink | Select any/all relevant records, searchable invoice selector; clear selection to unlink | GET `/material/invoice`, PUT `/material/inbound/batch-invoice` |
| inbound confirm and delete | Selected confirmation, row and batch deletion | POST `/material/inbound/batch_confirm`, `/material/inbound/batch-delete`, DELETE `/material/inbound/:id` |
| inventory editable stock, sales quantity/price, ratio, tax data | `/material/inventory`, native single-field edit, fresh server read, constant-sum quantity and dependent financial recalculation | PUT `/material/inventory/:id` |
| inventory supplier batch action | Labeled **销售商** because backend updates seller_id | PUT `/material/inventory/batch_supplier` |
| calculate sales | Selected rows; server owns stock-minus-pending and price-times-ratio calculation | POST `/material/inventory/batch_calculate` |
| outbound_add | Native inventory chooser and quantity dialog from outbound page; row shortcut from inventory | POST `/material/outbound` |
| outbound_batch_add | Selected inventory rows, saved sales quantities, direct-confirm switch | POST `/material/outbound/batch` |
| outbound delete / confirm / invoice | `/material/outbound`, row delete, selected confirmation, link/unlink | DELETE `/material/outbound/:id`, POST `/material/outbound/batch_confirm`, PUT `/material/outbound/batch-invoice` |
| outbound_records | `/material/outbound_records`, completed-only query, batch search, invoice actions | GET `/material/outbound?status=completed` |
| table export | Native XLSX export of filtered full result set | Client workbook export |

Material permission keys are `/view/material/<page>`. Invoice-library upload/OCR/edit/preview is owned by the core module and linked through `/material/invoice`; this module owns relationship changes. Ordinary outbound confirmation deliberately does **not** change stock, matching the existing endpoint. Direct confirmation in the batch endpoint does deduct stock. No frontend stock arithmetic substitutes for those server behaviors. The planning importer backend accepts the `.xls` suffix but uses openpyxl; true binary `.xls` may be rejected by the existing server and the error is surfaced.

## Nursery

| Legacy page / action | New route / action | API / storage |
| --- | --- | --- |
| dashboard | `/nursery/dashboard`, four metrics, category distribution, top five, recent transactions | GET `/nursery/dashboard/stats` |
| inventory | `/nursery/inventory`, complete stock list, search, paging, links to inbound/outbound | GET `/nursery/inventory` |
| inbound entry | `/nursery/inbound`, native form with category/location options, date/operator/remark | POST `/nursery/inbound` |
| inbound import / download template | XLSX template; workbook validation and preview; sequential independent submissions with per-row results | Client XLSX; POST `/nursery/inbound` for each row |
| outbound stock selection | `/nursery/outbound`, stock selector, fractional quantity/price, remove items, header metadata | GET `/nursery/inventory?all=1`, POST `/nursery/outbound` |
| outbound non-stock and settings products | Saved noninventory selector and custom lines, editable name/spec/unit/price | Same outbound payload with is_non_inventory true |
| orders edit | `/nursery/orders`, header/date plus quantities/prices by transaction ID | GET `/nursery/orders`, PUT `/nursery/order/:order_no` |
| orders delete and rollback | Confirmation explicitly explains stock restoration | DELETE `/nursery/order/:order_no` |
| orders details | Native detail dialog and printable receipt | Existing order items, browser print |
| logs edit/delete | `/nursery/logs`, clear warning that ledger edits do not adjust stock | PUT/DELETE `/nursery/transaction/:id` |
| history / transactions | `/nursery/history` and `/nursery/transactions`, type/search filter, full pagination | GET `/nursery/transactions`; permission `/nursery/transactions` |
| settings create/edit/delete | `/nursery/settings`, category, location, noninventory name/unit/guide price; legacy string migration | Same `localStorage.nursery_settings` key as original |
| export | XLSX of filtered full result set | Client workbook export |

Nursery server recalculates weighted average cost on inbound and handles stock rollback on order edits/deletes. Duplicate stock selection is checked using combined quantity. All financial/quantity form values remain strings until the existing API processes them. Imports prevalidate the workbook, do not retry completed/failed/uncertain rows, and stop on an uncertain network outcome. Logs remain ledger-only. Settings are browser-local, matching the original behavior.

## Validation and remaining acceptance

- `vue-tsc --noEmit` passed after final parity fixes; 35 module tests cover cached navigation and native checkbox selection (2026-09-24). Final integrated root build is still required.
- 19 domain tests verify fractional values, invalid quantities, duplicate stock selection, mixed stock/nonstock lines and settings migration.
- Thirteen mounted Vue tests verify exact generated inbound payload, batch outbound semantics, preservation of invoice linkage during inbound edit, order transaction identity/remark, success:false handling, submit locking, latest-stock inverse adjustment, project validation and dirty-dialog retention.
- Workbook tests exercise actual XLSX read, legacy header mapping and whole-file validation.
- All tests use mocked API or in-memory workbooks. No production writes or schema modifications.
- Real browser acceptance against an isolated database remains root integration work: inbound-to-stock-to-outbound, invoice relationship preview via core, import partial-success feedback, print rendering and permission-limited navigation. This document does not claim that end-to-end acceptance has passed.
- Existing backend arithmetic and quirks (ordinary material confirm behavior and binary XLS limitation above) are intentionally retained, not silently repaired in the frontend.

- Native forms have dirty dialog/route/reload protection, including outbound header drafts; active submissions block navigation. Inactive cached pages do not intercept reload. Print CSS is scoped to the active nursery print action.


- Cached Material/Nursery activation refreshes server queries and settings without resetting filter/page/editor state. Nursery outbound updates stock availability but retains user-entered quantities, prices and header data. Three real KeepAlive toggle regressions verify these behaviors. Status/type display is Chinese; monetary table values render two decimals without rounding quantities.


- Selection regression reproduced with real Element Plus controls: row checkbox and header select-all both cleared on each parent render because the template created a fresh sliced data array. Material and Nursery now use computed pageRows; native row click -> selected row -> generation dialog and header select/deselect tests pass. Header selection uses Element Plus 10 ms debounce. System tables were checked and already use stable data/computed bindings.

