# SmartHire — Microservices Guide (run & verify)

SmartHire runs as **independently deployable, fault-isolated services** in a
**monorepo** (uv workspace). The Week 1–2 scope is **fully split** and the legacy
monolith has been removed. This doc covers the layout, how to run it, and the
fault-isolation behaviour with the live results we observed.

For the design rationale see [architecture.md](architecture.md); for the
per-file reference see [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Services

| Service | Port | DB | Publishes | Consumes |
| --- | --- | --- | --- | --- |
| gateway | 8080 | — | — | — |
| auth | 8001 | auth | — | — |
| candidates | 8002 | candidates | `candidate.*` | — |
| jobs (+ Temporal worker) | 8003 | jobs | `job.*` | — |
| applications | 8004 | applications | `application.*` | `job.*`, `candidate.*` |

Infra: a Postgres per service (5433–5436), **Redis** (rate limiting), **Kafka**
(events), **Temporal** (+ UI on 8088) for job publishing.

## Repository layout

```
smarthire/
├── libs/smarthire_common/     # shared: config, database, security (RS256),
│                              # events (Kafka), enums, pagination, exceptions, logging
├── services/
│   ├── gateway/    app/(config, circuit, proxy, ratelimit, main) + tests
│   ├── auth/       app/(…) + migrations + tests + Dockerfile
│   ├── candidates/ app/(… , events) + migrations + tests + Dockerfile
│   ├── jobs/       app/(… , events, worker, publishing/) + migrations + tests + Dockerfile
│   └── applications/ app/(… , events, consumers) + migrations + tests + Dockerfile
├── keys/                      # dev RS256 keypair (gitignored; scripts/generate-keys.sh)
├── docker-compose.yml
└── pyproject.toml             # uv workspace root (package = false)
```

**Why `package = false`:** each service uses a top-level `app/` package. In a
shared workspace venv those would collide, so services are **run from source**
(not installed); only `smarthire_common` is installed. `pytest` adds each service
root via `pythonpath = ["."]`.

## Fault isolation — "one down ≠ others impacted"

- **Database per service** — no shared DB failure domain.
- **Stateless RS256 JWT** — auth signs with a private key; every service verifies
  with the public key, so auth downtime doesn't block authenticated requests.
- **Event-driven read-models** — `candidates`/`jobs` publish `candidate.*`/`job.*`;
  `applications` consumes them into local `candidate_refs`/`job_refs`. Apply-time
  eligibility is checked against those **local** copies, so applying works even
  when Jobs or Candidates is down. Consumers are idempotent; producer/consumer are
  fail-soft (a Kafka outage degrades eventing, never crashes a service).
- **Gateway circuit breakers** — each upstream has its own breaker; a failing
  service yields a fast **503** on its routes only, while `/health` and other
  routes stay up.
- **Rate limiting fails open**; **`/health`** = liveness, **`/ready`** = deps.

### Verified live (with real Kafka + Temporal)

- **Cross-service flow via the gateway:** create candidate (`candidate.upserted`)
  → create + publish job → Temporal drives it `processing → ready`
  (`job.upserted`) → **apply returns 201** (the applications service consumed both
  events into its read-models).
- **Fault isolation:** with the **jobs service stopped**, the gateway `/health`
  stayed **200**, `GET /api/v1/jobs` returned **503** (breaker), and **applying
  still returned 201** — served from the applications read-model.
- **Gateway ↔ auth:** killing auth returns a fast **503** on `/api/v1/auth/*` (no
  hang); after repeated failures the breaker opens ("circuit open").

## Run locally

```bash
# 1. Dev RS256 keypair (writes keys/, gitignored)
./scripts/generate-keys.sh

# 2a. Everything in Docker (DBs + Redis + Kafka + Temporal + all services)
docker compose up --build
#     Gateway → http://localhost:8080   ·   Temporal UI → http://localhost:8088
```

Run services from source (fast iteration):

```bash
uv sync --all-packages
# infra only
docker compose up -d auth-db candidates-db jobs-db applications-db redis kafka temporal temporal-ui

# migrate + run each service (example: auth)
cd services/auth
DATABASE_URL=postgresql+asyncpg://smarthire:smarthire@localhost:5433/auth \
JWT_PRIVATE_KEY_PATH=$PWD/../../keys/jwt_private.pem \
JWT_PUBLIC_KEY_PATH=$PWD/../../keys/jwt_public.pem \
uv run alembic upgrade head
DATABASE_URL=... JWT_PRIVATE_KEY_PATH=... JWT_PUBLIC_KEY_PATH=... \
uv run uvicorn app.main:app --port 8001
```

Other services follow the same pattern (ports 8002–8004, `JWT_PUBLIC_KEY_PATH`
only, `KAFKA_BOOTSTRAP_SERVERS=localhost:9094`; jobs also needs
`TEMPORAL_HOST=localhost:7233` and a worker via `uv run python -m app.worker`;
gateway needs the four `*_SERVICE_URL` vars). Full commands and env are in each
service's `.env.example`.

## Smoke test (through the gateway)

```bash
G=http://localhost:8080/api/v1
curl -s -X POST $G/auth/register -H 'content-type: application/json' \
  -d '{"email":"rec@x.com","password":"password123","full_name":"Rec","role":"recruiter"}'
TOK=$(curl -s -X POST $G/auth/login -H 'content-type: application/x-www-form-urlencoded' \
  -d 'username=rec@x.com&password=password123' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s $G/auth/me -H "Authorization: Bearer $TOK"
```

The Postman collection ([SmartHire.postman_collection.json](SmartHire.postman_collection.json))
covers every endpoint through the gateway and chains tokens/ids automatically.

## Tests

```bash
uv run ruff check libs services
cd services/auth         && uv run pytest   # 5
cd services/candidates   && uv run pytest   # 5
cd services/jobs         && uv run pytest   # 9  (incl. Temporal workflow)
cd services/applications && uv run pytest   # 9  (incl. read-model consumer)
cd services/gateway      && uv run pytest   # 4  (proxy 503 + breaker)
```

## Next (Weeks 3–5)

New capabilities land as **new services** consuming existing events, without
touching the current ones: `notifications` / `scoring` / `analytics` (Week 3,
alongside OpenTelemetry/Prometheus/Jaeger observability), `search` (Week 4,
embeddings + vector DB), `ai-assistant` (Week 5, LangGraph).
