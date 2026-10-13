# API

FastAPI serves the detailed schema at `/openapi.json` and `/docs` on the private API
listener. Public console traffic uses `/api/v1` through Caddy.

- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`
- `POST /orders/upload`: multipart CSV, <=64 KiB, 1–20 unique IDs, ISO dates.
- `POST /tasks`, `GET /tasks`, `GET /tasks/{id}`, `POST /tasks/{id}/cancel`
- `GET /tasks/{id}/events`: SSE, event IDs and Last-Event-ID reconnect support.
- `GET /tasks/{id}/export/json`, `GET /tasks/{id}/export/csv`
- `GET /operations`, `POST /operations/learn`
- `POST /operations/get_order_status/validate`, `.../repair`
- `POST /operations/submit_delivery_request/review`: exact candidate digest/version.
- `POST /requests/prepare`, `GET /requests`
- `POST /requests/{id}/approve`, `.../reject`, `.../submit`, `.../reconcile`
- `GET /receipts`, `GET /artifacts/{id}`
- `GET /metrics`, `GET /benchmarks`, `GET /audit-events`, `GET /system`
- `GET /scenario`, `POST /scenario`, `POST /containment`: admin only.
- `GET /health/live`, `GET /health/ready`

Mutations after login require `X-CSRF-Token` from the login/me response, plus the
HttpOnly session cookie. Client-supplied user IDs never establish ownership.
Errors carry HTTP status and explanatory content. Request IDs are response headers.

The suggested prompt route inventory was consolidated: operation detail/version data
is included in `/operations`; verification records are included in `/receipts` and
job results. There are no decorative unimplemented endpoint aliases.

## Provider setup (administrator only)

- GET `/api/v1/system/provider`: missing setting names and configured model IDs; no secret values.
- GET `/api/v1/system/models`: live public Vultr text catalog; no inference tokens used.
- POST `/api/v1/system/inference-check`: CSRF-protected explicit text probe, with audit
  measurements. Requires a configured key and a model present in the catalog. Uses
  inference tokens. Success verifies that one structured text call, not vision or
  browser learning. Provider failures are sanitized; no raw upstream error body is returned.

## User registration and roles

POST `/api/v1/auth/register` accepts only username and password. Usernames contain
3–40 lowercase letters, numbers, underscores or hyphens and start with a letter.
Passwords contain 12–200 characters. Duplicate names return 409. Invalid input,
including a caller-supplied role, returns 422. Cross-origin requests return 403.
Registration is limited to eight attempts per source in five minutes and creates
an authenticated HttpOnly session with a CSRF token. The server fixes the role to `user`.

- `user`: upload order CSVs, run existing read operations, cancel own tasks, inspect
  own records/evidence/exports and view operation definitions.
- `operator`: additionally prepare, approve and submit its own supplier requests.
- `admin`: additionally learn/repair/review operations, run baseline discovery,
  change scenarios and configure/test inference.

Public users cannot opt into operator/admin roles. Mutations require session CSRF
validation after registration. The shared synthetic portal is not a private supplier
catalog per tenant; task histories and evidence are private per account.
