# Verification record

Observed local verification completed on 2026-10-13. This is not production certification.

- Frontend TypeScript check: passed.
- Frontend production build: passed; chart/react chunks split, no bundle-size warning.
- Combined Python unit/security/API and actual Chrome tests: **41 passed** in
  127.08 seconds. One upstream Starlette/httpx deprecation warning remains.
  Tests use real persistence and explicitly deterministic provider fixtures.
- Actual local Chrome: read, unknown order, persisted write, layout-change detection,
  fixture-driven learning/repair, and timeout-after-persistence reconciliation passed.
  These are browser behavior tests, not Docker containment proof.
- Console Playwright test: passed login, upload, queue, cancel, library, scenario
  switch and logout. Screenshots in `docs/screenshots` are from actual execution.
- PostgreSQL Docker services: migrations and startup passed.
- Docker boundary probes: deadline kill/removal, memory OOM enforcement, orphan
  reaper, and network reachability restrictions passed. See container-probe-results.json.
- Full Docker browser workflow: **passed** with PostgreSQL, API, disposable
  Chromium containers and persistent portal. Covered learning, regression validation,
  three-order reuse, exact approval, persisted submission, duplicate prevention,
  layout-change detection, repair, reuse after repair, deadline termination and
  application health afterward. See acceptance-measurements.json.
- Updated full-stack console Playwright tests: **2 passed**. Revalidation ran the
  real six-case browser suite and created a fresh version. The UI compared versions,
  rejected an invalid replacement CSV, returned an expired session to login and
  signed out at mobile width. It then reviewed the new write version, approved an
  exact request and displayed the independently persisted result. Individual test
  durations were 31.3 and 8.5 seconds. The earlier console-navigation test also passed.
  Actual screenshots: screenshots/version-comparison.png, screenshots/approval.png
  and screenshots/verified-execution.png.
- Learning and repair acceptance used **TEST_FIXTURE_NOT_AI** proposals. The normal
  runtime has no fixture-provider switch; the seeded test operations remain visibly
  labeled in this local demonstration database.
- Local production frontend is running at http://localhost:8080 through Caddy.
- Live Vultr model learning/vision: not run; credentials and model IDs absent.
- Vultr VM/HTTPS deployment: not performed; no VM access or domain supplied.
- Performance improvement claims: none.

The Chromium sandbox remained enabled. The seccomp profile permits chroot inside
Chromium's user namespace; browser containers still drop all outer capabilities.
Probe results establish only their stated checks, not resistance to every escape.
The trusted Docker supervisor can control the host Docker daemon and requires an
isolated worker host in the intended production topology.

Optional MCP export, arbitrary-site support, signed attestations and a visual
workflow editor are not implemented. See limitations.md for scope boundaries.
No comparative AI performance result, public deployment or real Vultr inference
success is claimed. Those require actual credentials, configured model IDs and
deployment infrastructure.

The final regression suite also covers expired-version renewal without rewriting
history, failed renewal without promotion, canceled reads, and malformed provider
response envelopes. Docker and production frontend images were rebuilt and the
local services restarted with their existing data preserved. Readiness returned ok.

## Provider setup and launcher follow-up (2026-10-13)

- Backend suite: 45 passed, 3 optional local-browser tests skipped, 12.55 seconds.
  The earlier 41-test run above included those actual-browser tests. Browser runtime
  code did not change in this follow-up.
- UI checks: recovery/revalidation and the new setup-panel test passed. The approval
  test initially checked for its review button before operation data loaded; after
  adding a data-loaded wait and unique request text, its rerun passed in 10.7 seconds.
  The setup-panel error/missing-key checks explicitly use HTTP fixtures, not real AI.
- Production frontend build passed locally and in Docker. Updated services are running.
- Actual public Vultr catalog discovery succeeded and returned 13 text model IDs.
  No authenticated inference or vision call was performed; key and model settings
  remain missing. Catalog retrieval is not credential verification.
- The WSL launcher passed syntax and actual status/start checks after replacing
  fragile nested command quoting with a fixed shell entrypoint. Existing data was retained.
- Provider checks are administrator-only; the billed text probe requires CSRF.
  Focused tests cover missing configuration, malformed catalog, model mismatch,
  configured-secret non-disclosure, and role/CSRF enforcement.

## Self-signup and user login (2026-10-13)

The user explicitly requested self-signup, superseding the earlier operator-only
login preference. New accounts receive the restricted `user` role. Operator writes
and administrator controls remain protected in both the API and the UI.

- Backend regression run: 49 passed, 3 optional browser tests skipped, 42.99 seconds.
  Covered password hashing, login/logout, duplicate names, invalid input, origin
  checks, role injection, signup throttling, private task access and operator restrictions.
- Production frontend builds passed on Windows and in the Docker image.
- Real Docker/Chrome UI acceptance: 3 passed in 1.1 minutes. A new user signed up,
  executed a verified read task, logged out/in, and a second account was denied
  access to that task. Existing operator approval/submission and recovery flows passed.
- Screenshot of the actual restricted user workspace: screenshots/user-workspace.png.
- Existing database records and operator credentials were preserved. No schema
  change or new privileged account was required. Test-created users hold synthetic
  records and randomly generated test passwords.

These checks do not add live Vultr credentials, email verification, password recovery
or enterprise tenant isolation. The shared supplier catalog remains synthetic.


## Five priority improvements (2026-10-13)

Implemented local live-provider acceptance preparation, failure classification,
sample-order onboarding/readiness, linked recovery evidence and controlled paired
benchmarks. The user requested local preparation because Vultr infrastructure is
not available yet. See hackathon-readiness.md for remaining submission evidence.

Validation of the final changes:

- Non-browser backend suite: **67 passed**, four browser cases deselected.
- Real Chrome browser cases: **four passed across two focused batches**. Covered
  reads, writes, changed selectors, observed learning/repair with a clearly labeled
  test-only provider, access denial, and timeout reconciliation without resubmission.
  A preceding run exposed a navigation timing classification bug; the fix checks
  target presence before the action, and both affected and ordinary browser paths
  were rerun successfully. These learning/repair cases do not prove live AI behavior.
- Production TypeScript/Vite builds passed on Windows and in Docker.
- Full Docker/Chrome UI suite: **3 passed in 57.1 seconds**. Covered sample order
  loading, readiness, immutable validation, stale CSV rejection, session expiry,
  approved submission/receipt, self-signup and private cross-account task access.
- Final service/browser images rebuilt; localhost health returned `status: ok`.
  Existing database volumes and operator credentials were retained.
- Tracked source scan found no configured private environment secret values.
- Live acceptance preflight correctly reports missing Vultr key/chat/vision model
  IDs, no public HTTPS URL and no independently verified cloud execution.

No real-provider benchmark, authenticated inference/vision acceptance, public Vultr
deployment or new recorded submission video was performed. Benchmark unit tests use
test doubles only inside tests. Runtime benchmarks require actual provider settings
and consume real tokens. JSON exports retain partial timeline measurements and
candidate evidence; missing trials or usage are never represented as success/zero.
