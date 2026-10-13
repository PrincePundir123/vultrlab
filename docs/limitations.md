# Implementation boundaries

The runtime has no test-provider switch. A deterministic inference provider exists
only under tests and the explicitly labeled acceptance driver. Actual model calls
use Vultr; availability must be verified with your subscription and model IDs.

Implemented choices narrower than the full aspirational prompt:

- Only controlled synthetic portal, no third-party login sessions.
- Single orchestrator; no horizontal scheduler scaling.
- Local/single-VM overlay shares a kernel; preferred two-VM resources are supplied
  but cross-VM Vultr deployment is externally unverified.
- Read-only AI learning and automatic repair. Write steps use reviewed fixed composition.
- Immutable version history and field-by-field workflow/contract comparison; no visual workflow editor or MCP server.
- Metrics record actual runs. Controlled comparative benchmark conclusions remain pending.
- Model summaries are not necessary for completion; UI shows observed events and
  deterministic explanations instead of adding an extra explanation-agent call.
- Portal schema is initialized by its service; control-plane schema uses Alembic.
- API route inventory is consolidated; see api.md.
- Artifact hashes are not cryptographic signed attestations.
- Portal form permissions depend on this controlled portal's known semantics.

External prerequisites and test status are recorded separately in verification-report.md.
