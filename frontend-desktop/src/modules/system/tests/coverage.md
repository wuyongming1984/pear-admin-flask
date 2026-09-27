# Desktop system migration coverage

| Legacy page | Desktop route | Preserved operations / endpoints |
|---|---|---|
| system/user/index.html | /system/users | Load all paginated users, local search/page, create/edit/delete /user/, explicitly assign or clear /user/user_role/:id; blank/masked edit password omitted; creation keeps server default; no automatic grants |
| system/role/index.html | /system/roles | Create/edit/delete /role/; fetch rights tree and own rights; independent checkbox state saves /role/role_rights/:id, including empty grants |
| system/department/index.html | /system/departments | Entire nested /department/treetable with paginated roots; create/edit/delete; enabled state, leader, parent selection excluding self and descendants; server rejects occupied deletion |
| system/rights/index.html | /system/rights | Entire nested /rights/treetable; create/edit/delete; menu/path/auth, code, URL, icon, enabled state, ordering, opening mode, parent selection; enable status through edit |
| system/dictionary/index.html | /system/dictionary | Search dictionary code/description; dictionary CRUD; choose dictionary and CRUD detail code/value/order; preserve selection scope and discard stale detail loads |
| system/backup/index.html | /system/backup | Load/save /system/config/backup; automatic schedule; preserve masked secret when blank; explicit confirmation before POST /system/backup/test; response log |
| view/system/person.html | /profile | Read-only current profile; validate original/new/confirmation and POST /user/change-password |
| portal/reconcile.html | /reconcile/:token | Public scoped GET /portal/reconcile/:token/data; totals, project grouping, orders, linked/unlinked payments and payment parties/purpose; invalid-token error and refresh; browser print |

The public endpoint is owned by root and uses exactly the existing legacy token resolution and contact grouping. This module never queries unscoped supplier/order/payment APIs from the public page. Legacy template quantity/unit/price references do not exist in OrderORM; these render only if the server supplies them.

## Verification

`node node_modules/vitest/vitest.mjs run src/modules/system/tests`:
- helper tests check descendant parent exclusions, empty/masked credential preservation, backup-secret preservation, independent explicit grants, password validation.
- Vue component tests mock every API: user edits preserve fields and never grant roles; role assignment starts with owned roles and can clear all; failed authorization fetch cannot silently save; backup config saves masked secret and never executes backup.

Tests do not connect to a database, execute a backup, send email, or change a schema. Production backup execution deliberately remains untested. Shared request must reject both nonzero code and success:false dictionary responses (root implemented).

Remaining integration acceptance: isolated-database real browser pass through each CRUD route, nested-role permission semantics and public invalid/valid token comparison. Component/unit tests alone are not a claim of end-to-end acceptance.

- Portal component tests assert the token-only endpoint, scoped totals, and removal of old supplier data after a changed/invalid token. Final module run: 11 tests passed across 3 files; vue-tsc --noEmit exit 0.

## Unsaved form protection
System editor dialogs, role/permission grants, dictionary details, profile password fields and backup configuration now track drafts. Cancel/X/Escape, route leave/update and browser unload protect changes. Active submissions cannot be discarded. Backup Reload confirms before overwriting edits. Cached inactive components disable their unload warning. Guard and component regressions: 19 tests pass (4 files); TypeScript check exit 0.
