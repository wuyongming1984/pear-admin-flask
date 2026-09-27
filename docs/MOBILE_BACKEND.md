# Mobile API compatibility

The mobile client uses the existing JWT-protected `/api/v1` APIs. Supply the desktop login token as `Authorization: Bearer <token>`. Business responses retain the existing `{code, msg, data}` convention (`code: 0` succeeds, `-1` fails); list responses also include `count`.

- `GET /api/v1/project/<id>` returns the same project object as the list, including `attachments_list` and legacy JSON-string `attachments`. Missing IDs return the normal failure envelope.
- `GET /api/v1/order/?project_id=<integer>` adds an exact project filter. Existing `project_name`, pagination, and other filters remain available and combine with it.
- Successful project, order, and payment POST responses include `data.id`.
- Payment detail/list objects now include raw `attachments`, alongside the existing signed `attachments_list`. Use the raw value for editing so temporary signed URLs are not saved.
- `GET /m/` serves `static/mobile/index.html` with `Cache-Control: no-cache, no-store, must-revalidate`. The SPA uses hash routing; build assets are served by Flask's existing static route.
- Nested `/uploads/<path>` downloads use the current `UPLOAD_FOLDER` and Werkzeug safe path joining. The existing more-specific flat `/uploads/<filename>` route remains unchanged (including its historical dev-config behavior).

## Project saves

Project fields and attachment changes commit together. Invalid JSON, invalid attachment entries, missing IDs, duplicate IDs, foreign-project IDs, invalid dates/amounts, and persistence failures return a failure envelope and roll back the whole save.

Omitting `attachments` preserves attachments. Providing a list or JSON-encoded list replaces the attachment set; `[]` explicitly removes all attachment rows. `null` is invalid. Each new attachment requires a nonempty `code`, file path (`file_path` preferred, or `url`), and filename (`filename`, `name`, or derivable from the path). `size` defaults to zero and must be a nonnegative integer. Existing attachment IDs may be strings or integers, must belong to the current project, and retain their stored file metadata. On create, only genuinely unassigned existing attachment IDs are accepted; the current schema normally prevents unassigned rows.

Payment edits continue preserving invoice links when `invoice_ids` is omitted. No tables, migrations, authentication policy, or production settings were changed.

## Offline regression tests

From the repository root in PowerShell:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p test_mobile_api.py -v
```

Tests initialize Flask, SQLAlchemy, JWT, and API blueprints manually against SQLite in memory. They do not call the application factory, initialize OSS, start the scheduler, read or write the instance database, or contact cloud services. Socket connections are blocked during each test. Temporary upload and mobile HTML fixtures are removed on completion.

The suite includes a complete project → order → payment create/edit flow, with Chinese-named PNG/PDF multipart uploads for all three record types. Downloads are compared byte-for-byte with the uploaded files. It checks exact relationship filters, preservation of original attachment data and invoice links on ordinary edits, attachment IDs retained when appending a project attachment, and identical `sqlite_master` table/index/schema definitions before and after the complete flow. OSS storage is explicitly disabled inside the fixture.

A real expired JWT is generated locally and submitted through the API. The expired-token callback accepts the header/payload arguments required by Flask-JWT-Extended and preserves the existing HTTP 403 `{code: -1, msg: "token 已过期，请重新登录"}` response. This fixes the previous callback-signature exception without changing token policy.

Project/default upload filenames now split the original extension before sanitizing the basename, then append a full UUID to the timestamp. Chinese-only names retain `.jpg`/`.pdf`, and multiple uploads in the same second cannot overwrite each other through the old timestamp-only naming collision. Storage directories, original filename metadata, and response fields remain unchanged. A frozen-clock regression uploads two different Chinese-only names for both JPG and PDF, checks distinct URLs and preserved extensions, then rereads both files to verify their independent contents.
