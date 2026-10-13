# Implementation record

Independent implementation of the supplied Skeleton Key Guard specification.

## Boundaries

- React console calls a FastAPI control plane. PostgreSQL holds durable jobs, users,
  immutable operation definitions, approvals, evidence and audit records.
- The inference adapter lives only in the control plane. No provider secrets enter
  generated workflows or browser containers.
- A trusted worker supervisor launches one disposable browser per observation or
  execution. Learning replays bounded prefixes in fresh containers, trading speed
  for a small, inspectable lifecycle.
- A synthetic supplier portal has a separate persistent database and a protected
  read-only truth interface. Browser access and internal administration are distinct.
- The deterministic policy validates every action. The independent verifier checks
  actual persisted portal records, never candidate-reported success.
- Only controlled operator accounts can write. No public guest writes or arbitrary URLs.

## Build order

1. Schemas, policy, persistence, supplier portal, session authentication.
2. Browser interpreter and disposable Docker supervisor; real observation evidence.
3. Durable orchestration, inference learning, operation validation and repair.
4. Exact approvals, reconciliation, receipts, exports.
5. Connected React console, security tests, integration tests, measurement recording.
6. Deployment resources, reproducible acceptance scripts and honest verification report.

## Environment discovered

Windows host, Python 3.14 and Node 24. Docker runs through Ubuntu WSL, with Python
3.12 in application containers. The complete local Docker workflow and browser UI
approval flow passed; the combined Python/Chrome regression suite passed 35 tests.
The application is available at http://localhost:8080. No Vultr credentials are
configured. Learning/repair acceptance uses explicitly labeled test fixtures;
real model execution and cloud deployment remain externally unverified. See
docs/verification-report.md for evidence and docs/limitations.md for deferred scope.
