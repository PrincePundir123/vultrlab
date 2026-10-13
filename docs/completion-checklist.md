# Completion and handover

Self-signup is available. New accounts receive the restricted user role; supplier
submissions remain operator-only, and administrative controls remain admin-only.

| Requirement | Implementation and evidence |
| --- | --- |
| Supplier portal, CSV, browser execution | Persistent synthetic portal; strict CSV parsing; real disposable Chromium runs |
| Learning and repair | Vultr-only adapter; bounded proposals; six regression cases; deterministic test-only acceptance |
| Reusable permissions and versions | Immutable definitions, fixed action policy, origin checks, expiration, tested revalidation |
| Approval and verification | Exact snapshots, single-use approval, persisted independent verification, uncertainty reconciliation |
| Progress and receipts | Durable jobs, SSE timeline, screenshots, owner-scoped JSON/CSV exports |
| Regression and recovery | Candidate tests before promotion; failed history retained; quarantine; comparison view |
| Containment | Resource limits, deadlines, network restrictions, cleanup; recorded Docker probes |
| Metrics | Actual durations and provider usage; no claimed speedup without comparative trials |
| Deployment | Local Docker stack and one/two-VM Vultr manifests; CI and deployment guide |

## External steps that remain

1. Privately configure VULTR_INFERENCE_API_KEY and actual VULTR_CHAT_MODEL in .env;
   optionally configure a supported VULTR_VISION_MODEL. Never put these in GitHub.
2. Recreate the API and orchestrator containers to load the new environment. Use
   Operation Library to learn again and verify that the provider is Vultr, not a test fixture.
3. Run the demo storyboard and comparative trials using real model calls, preserving failures.
4. Provision Vultr infrastructure, configure private networking and a domain, deploy
   using deployment.md, then verify HTTPS and repeat acceptance there.
5. Record the public demo and submit the deployment link, repository and measured results.

These steps require the user's provider account, credits and infrastructure. No API
key, live model success, public deployment or recorded submission is fabricated.
MCP export, microVM isolation and additional portals remain optional P2 scope.
