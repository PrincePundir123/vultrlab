# Local and Vultr deployment

Prerequisites: Linux Docker Engine, Compose v2, outbound package/image downloads,
Linux iptables, 4+ GB RAM available to Docker, Python 3.12+ for setup scripts.
Windows users run Docker inside Ubuntu WSL2 or Docker Desktop's Linux environment.
The firewall script must execute on the actual Docker host. Docker Desktop's managed
VM may need a different verified firewall setup; Ubuntu WSL Docker is the tested target
when available. Never skip egress enforcement to make a demonstration work.

```bash
python infra/scripts/setup_env.py
# Edit .env privately: add Vultr key and real available model identifiers.
sudo bash infra/scripts/network.sh
docker build -f infra/docker/browser.Dockerfile -t skg-browser:local .
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 api orchestrator worker
```

Open http://localhost:8080. Read the generated OPERATOR_PASSWORD in your local .env;
do not commit it or share it in screenshots. The browser image must exist before
execution. Migrations and bootstrap run as the `migrate` one-shot service.

Check model availability using Vultr's authenticated `/v1/models` API or official
console. Configure VULTR_CHAT_MODEL and optionally VULTR_VISION_MODEL from actual
available identifiers. Blank settings produce an explicit unavailable error.

## Vultr

The preferred two-VM configuration is `infra/vultr/control.yml` plus
`infra/vultr/worker.yml`. These resources are supplied but cross-VM cloud connectivity
has not been tested without VM access. The local Compose and production overlay are
a single-VM option for development or limited-resource demonstrations; they share
a kernel and administrative failure domain.

For two VMs, place both in a Vultr private network. On the worker, create `.env.worker`
from `infra/vultr/worker.env.example`, sharing only the two internal authentication
secrets with the control plane. Bind ports 8091/8092 to the worker's private IP and
permit only the control VM at the cloud firewall. Do not open those ports publicly.
On the control VM, set WORKER_INTERNAL_URL=http://worker-private-ip:8092 and
PORTAL_INTERNAL_URL=http://worker-private-ip:8091. Set PORTAL_BASE_URL consistently
to http://172.30.90.2:8090 (the browser network's fixed portal origin).

Worker commands, from repository root:

```bash
sudo bash infra/scripts/network.sh
docker build -f infra/docker/service.Dockerfile -t skg-service:local .
docker build -f infra/docker/browser.Dockerfile -t skg-browser:local .
docker compose --project-directory . --env-file .env.worker -f infra/vultr/worker.yml up -d
```

Control commands:

```bash
docker compose --project-directory . -f infra/vultr/control.yml up -d --build
```

For the single-VM option:

1. Create an Ubuntu Vultr VM with enough memory for two 1.5 GB browser containers
   plus control services. Start with at least 8 GB if running both worker slots.
2. Install Docker and Compose from their official instructions. Clone/copy this repo.
3. Generate .env, set APP_BASE_URL=https://your-domain, COOKIE_SECURE=true,
   PUBLIC_DOMAIN=your-domain and actual Vultr inference credentials/model IDs.
4. Point DNS at the VM. Only expose TCP 80/443 and restricted administrative SSH.
   Do not publish DB, API, worker, portal or portal-admin ports.
5. Apply network.sh; build browser; run:

```bash
docker compose -f docker-compose.yml -f infra/vultr/production.yml up -d --build
```

6. Check HTTPS, inference, actual screenshots, approved submission and independent
   receipt. Record a real containment test. The repository does not itself establish
   that a cloud deployment occurred.

## Integration acceptance

```bash
docker compose stop orchestrator
docker compose cp tests api:/app/tests
docker compose cp infra/scripts/integration_acceptance.py api:/app/acceptance.py
docker compose exec api python /app/acceptance.py
docker compose start orchestrator
```

This uses a deterministic **test-only** inference provider and real browser containers.
Its contracts are labeled TEST_FIXTURE_NOT_AI. Run real learning again with Vultr
before recording a public AI demo. Inspect output rather than assuming it passed.

## Operations

- Restart: `docker compose restart api orchestrator worker`.
- Migration: `docker compose run --rm migrate`.
- Health: `/health/live` and `/health/ready`; console displays worker readiness.
- Back up PostgreSQL using `pg_dump`; stop portal services before copying its SQLite
  volume. Back up artifacts alongside database metadata.
- Reset only this demo: stop all project services, back up volumes, then explicitly
  remove the project's database/portal volumes if you intend to erase all records.
  Do not use global Docker prune commands.
- Stop charges: `docker compose down` stops software but **does not stop VM billing**.
  Destroy unused Vultr resources through your account after preserving data.
- Set provider spending limits and monitor credits. No dollar cost forecast is claimed.
- Reapply and verify firewall rules after reboot. Persist them using your host's
  normal firewall management after reviewing conflicts.

Official references: [Vultr inference](https://docs.vultr.com/products/compute/serverless-inference/provisioning),
[Playwright Docker](https://playwright.dev/python/docs/docker),
[Docker security](https://docs.docker.com/engine/security/).
