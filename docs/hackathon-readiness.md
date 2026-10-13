# Hackathon requirement and evidence map

Reference checked 2026-10-13: https://lablab.ai/ai-hackathons/vultr-hackathon

| Requirement | Local implementation | Evidence still required for submission |
| --- | --- | --- |
| Vultr VM backend and isolated execution | One/two-VM Compose resources and resource-limited browser worker | Actual VM deployment, region and configuration |
| Agent LLM calls through Vultr | Pinned Vultr inference adapter | Real learning and repair runs |
| Browser screenshots and vision | Screenshot artifacts, supplemental vision adapter, independent persisted verification | Actual supported vision model run |
| Public browser app | React/Caddy app, signup and private task histories | HTTPS URL reachable by judges |
| Resource limits and cleanup | Deadline, memory, network and cleanup probes | Recorded containment moment on Vultr |
| Repository, architecture and use case | MIT source, architecture, threat model and demo storyboard | Public repository and final submission materials |
| Demo video, slides and cover | Storyboard supplied | Record/export final assets from the real deployment |

## Live acceptance

Privately configure actual provider key/model IDs and the deployment URL in .env.
Run from the control plane or a trusted local environment with project dependencies:

```bash
python -m guard.live_acceptance
python -m guard.live_acceptance --run
```

The first command performs configuration checks only. The second uses real tokens,
learns, executes, explicitly approves one synthetic request, requires actual vision,
changes layout, repairs, executes again and checks containment and application health.
It never injects a fixture provider. Output defaults to ignored artifacts/live-acceptance.json.
Failed checks leave their real jobs and partial report available; inspect before retrying.
The synthetic portal is left at v2; the repaired write version needs review before later writes.
Do not run this while others are using the shared demonstration portal.

The report cannot attest VM location or create a video. Even a successful local run
does not meet the public deployment requirements. Never describe fixture evidence
as live AI or claim guaranteed hackathon eligibility based solely on this checklist.
