# API

FastAPI serves the detailed schema at `/openapi.json` and `/docs` on the private API
listener. Public console traffic uses `/api/v1` through Caddy.

- `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`
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
