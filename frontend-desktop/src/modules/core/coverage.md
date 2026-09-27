# Core desktop migration coverage

Module entry: `routes.ts` default export (`RouteRecordRaw[]`). Every nested route has the actual legacy `meta.menuPath` for permission mapping. Only this module directory was changed. No production API calls or database mutations were performed while implementing or testing this module.

| Legacy screen | Native routes | Implemented behavior and API |
| --- | --- | --- |
| `/project/info/project_info.html` | `/projects`, `/projects/new`, `/projects/:id`, `/projects/:id/edit` | Server search/pagination, dictionary scale/status, all project fields including dates/three amounts, create/update/delete, linked order navigation via `project_id` query, attachment upload/list/remove and required attachment codes. `/project/`, `/project/:id`; root AttachmentEditor `/upload/`. |
| `/supplier/info/supplier_info.html` | `/suppliers` and new/detail/edit | All supplier fields, type dictionary, every server search field, create/update/delete. Contact-change `1001` response displays all affected orders and requires explicit full confirmation before `/supplier/:id/update-with-orders`. Generate/reset native `/pc/#/reconcile/<token>` reconciliation link through `/supplier/:id/token`. |
| `/payer/info/payer_info.html` | `/payers` and new/detail/edit | Unit/person type, name, bank, account, remarks; server search/pagination and CRUD. Because backend has no GET-by-ID, detail loads all paginated payers with the shared guarded `allRows` helper. |
| `/order_pay/base/order_base.html`, `/order_pay/info/order_info.html` | `/orders` and new/detail/edit | All writable order fields, complete project/supplier/material selectors, supplier phone/contact auto-fill, all backend search fields, attachment edit, existing created time preserved, exact decimal input, generated number when empty, linked payment table and new-payment navigation, current-page amount/paid/balance totals. Order relationships are navigable in native routes. |
| `/order_pay/base/pay_base.html`, `/order_pay/info/pay_info.html` | `/payments` and new/detail/edit | All writable payment fields, order/payer/payee selectors, account and order summary, invoice multi-selection with existing associations preserved, attachments, CRUD, every backend textual search field, detail invoice links. New payment number uses a timestamp-based FK prefix; backend uniqueness remains authoritative. |
| `/view/material/invoice`, `/view/material/invoice/add`, `/order_pay/info/invoice_detail.html` | `/invoices` and new/detail/edit | Paginated keyword/project/buyer/seller/number search; category filter across all matching rows; manual create; multifile upload with project/storage path and returned per-file results; explicit OCR/re-OCR action and results; single/batch delete; category/deductible/remarks edit; complete returned invoice fields, detail rows/raw OCR/error, file preview/open original; reverse payment associations. `/material/invoice`, `/material/invoice/upload`, `/material/invoice/ocr`. |
| `/order_pay/info/print_order.html` | `/orders/:id/print` | Native Vue port of original A4 approval markup/styles: every original field, payment history, attachment names, approval lines, QR. Material dictionary display. |
| `/order_pay/info/print_pay.html` | `/payments/:id/print` | Native Vue port of original A5 landscape markup/styles: payer/payee/bank account, purpose, exact amount and uppercase amount, order/project/material, cumulative payment/progress/balance, handler/approval grid/verification QR. Long purpose and project names are not clipped. |

All lists offer CSV export of **all matching records**, including category filtering, with spreadsheet formula-injection escaping. Financial input and outgoing payloads stay decimal strings. Detail-only relationship objects never enter ORM mutation payloads. Existing writable fields/created timestamps/attachment identities/invoice IDs are retained. Read/submit failures show an error and preserve the draft. Submit/upload operations are locked; no mutation auto-retries. Leaving or reloading a dirty form prompts; cached editors capture their own route metadata and keep drafts across module navigation. Cached lists refresh on reactivation. Print styles and paper size are limited to the active print route.

## Verification completed

- `vue-tsc --noEmit`: passed after final route-cache fix.
- `vitest run src/modules/core`: 29 tests passed, no unhandled errors or Vue warnings.
- Tests cover exact amounts, attachment identity/malformed attachment refusal, relationship payload preservation, invoice writable whitelist, required/money validation, true menu URLs, uppercase printed amounts, pending-submit deduplication, failure draft retention, successful-create draft reset, successful navigation, and KeepAlive cross-module draft preservation/no wrong API requests.

## Remaining acceptance checks and explicit differences

- Browser interaction against an isolated database, real upload/OCR provider integration, and rendered/PDF print comparison remain root integration acceptance work. Unit tests do not prove external storage/OCR availability or physical paper pagination.
- Order grouping uses search filters plus a full linked-payment table in detail, rather than the legacy collapsible list presentation. Amount totals are explicitly labelled **current page**; no unlabelled whole-dataset total is asserted.
- Native column visibility controls and current-page table print previews are implemented for all core lists; table print uses the selected columns. Full-query CSV and dedicated order/payment approval prints remain available. Invoice detail now includes the original ticket-style buyer/seller grid, all eight item columns, totals, remarks and footer signatories alongside original-file preview.
- Invoice edit intentionally exposes only the three fields the existing PUT endpoint persists. Other invoice fields are viewable; manual creation and explicit OCR populate them. No claim of unsupported arbitrary invoice-field editing.
- The original print templates' remote fonts were removed in favor of local font fallbacks. QR is generated locally via the bundled `qrcode` dependency. Long payment purposes may flow onto another printed page instead of being silently clipped.
- Invoice reverse payment links currently scan paginated payment records; very large installations would benefit from a dedicated filtered backend endpoint. Shared `allRows` reports its cap instead of silently omitting records.



Print follow-up: old embedded print buttons removed; approval actions use the shared Element Plus toolbar. Decimal display rounds/pads through decimal strings and BigInt without changing outgoing values. Order picker material codes resolve through dictionary35 labels. Print component tests cover these behaviors.


Final invoice states: missing original files show an empty state without an empty href/object; OCR lifecycle status labels are Chinese. Regression test mounts the manual invoice detail to verify both.

