# Verification record

Observed local verification completed on 2026-10-13. This is not production certification.

- Frontend TypeScript check: passed.
- Frontend production build: passed; chart/react chunks split, no bundle-size warning.
- Combined Python unit/security/API and actual Chrome tests: **35 passed** in
  81.71 seconds. One upstream Starlette/httpx deprecation warning remains.
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
- Full-stack console Playwright test: **1 passed** in 12.1 seconds. An actual Chrome
  session reviewed the write version, prepared and approved an exact request,
  submitted through the running orchestrator/Docker worker, and displayed its
  independently verified receipt. See screenshots/approval.png and
  screenshots/verified-execution.png. The separate console-navigation test also passed.
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
operation diff editor are not implemented. See limitations.md for scope boundaries.
No comparative AI performance result, public deployment or real Vultr inference
success is claimed. Those require actual credentials, configured model IDs and
deployment infrastructure.
