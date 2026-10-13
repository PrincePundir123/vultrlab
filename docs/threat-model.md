# Threat model

Trusted: operator accounts, control-plane code, policy definitions, verifier,
worker supervisor, controlled portal implementation, Docker host administrator.
Untrusted: uploaded CSV, goal text, model JSON, webpage content, workflow outputs.

Enforcement:

- Restricted JSON vocabulary; no model eval, shell commands or dynamic imports.
- Semantic targets use a restricted character set and action-specific allowlists.
- Read execution cannot fill request fields or click Submit. Request interception
  separately rejects POSTs unless the exact approved form fields match.
- Independent Linux firewall blocks sandbox access to the host and destinations
  other than the portal listener. An internal bridge alone is not the entire policy.
- Browser container is non-root, read-only, drops capabilities, disallows privilege
  escalation, has memory/process/CPU/deadline limits, and receives no secrets.
- Chromium's own sandbox remains enabled. A launch failure must not be fixed by
  adding `--no-sandbox`, host IPC, privileged mode or SYS_ADMIN.
- Hostile page instructions remain data; policy cannot be changed by model JSON.
- Argon2 password hashes; opaque server-side sessions, HttpOnly SameSite cookies,
  CSRF token checks, origin checks, expiration, durable login attempt limits.
- Jobs, drafts, exports and artifacts are owner restricted, including administrators.
- Write approval binds to operation version, definition hash, exact order/message,
  idempotency key, owner, origin and policy revision. Atomic consumption prevents reuse.
- Portal unique idempotency keys reject conflicting payloads. Timeout reconciliation
  uses persisted state before any decision; uncertain writes are not resubmitted.

Residual risks and limits:

- Docker shares a host kernel and is not a complete defense against kernel escapes.
- Docker supervisor effectively has host administrative authority. Keep it private.
- The network label is an installation assertion; run the network probes after host
  restart or firewall changes. Reapply the firewall script after reboot.
- Portal data is synthetic and shared among controlled operators, not enterprise tenant
  isolation. No public signup or guest write access is implemented.
- Real third-party credentials, sessions, CSRF handling and arbitrary web origins are
  explicitly unsupported. No claim of arbitrary-site login isolation is made.
- Exact request interception is controlled-portal-specific. It is not a generic
  semantic defense against all websites.
- Evidence hashes detect accidental modification; they are not signed attestations.
- One orchestrator is supported. Horizontal scheduling and distributed locks are
  future work; do not scale the orchestrator service above one replica.
- No production security certification or universal novelty claim.
