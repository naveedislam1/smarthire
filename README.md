# SmartHire — Intelligent Workforce Orchestration & Recruitment Platform

Backend for **SmartHire**, TalentSphere Inc.'s recruitment automation platform —
built as **fault-isolated microservices** in a monorepo (uv workspace).

> **Status:** Week 1–2 delivered and split into independent services.
> Job & candidate management, JWT auth (RBAC), the candidate application
> workflow, and a **Temporal**-orchestrated job publishing pipeline — each
> running as its own deployable service with its own database, communicating over
> **Kafka**. If one service goes down, the others keep working.

Deep dives: [docs/microservices.md](docs/microservices.md) ·
[docs/architecture.md](docs/architecture.md) ·
[docs/week-2-implementation.md](docs/week-2-implementation.md)

## Services

| Service | Port | Database | Role |
| --- | --- | --- | --- |
| **gateway** | 8080 | — | Single entry point: routing, JWT-aware proxy, per-upstream circuit breakers, Redis rate limiting |
| **auth** | 8001 | auth | Users; issues RS256 JWTs (access + refresh) |
| **candidates** | 8002 | candidates | Candidate + profile management; emits `candidate.*` events |
| **jobs** (+ Temporal worker) | 8003 | jobs | Job management + publishing workflow (`processing → ready`); emits `job.*` events |
| **applications** | 8004 | applications | Apply workflow (duplicate/eligibility/limit/idempotency, stage tracking); keeps local read-models from `job.*`/`candidate.*`; emits `application.*` |

Shared code (config, async DB, RS256 security, Kafka events, errors) lives in
`libs/smarthire_common`.

## How fault isolation works

- **Database per service** — no shared DB failure domain.
- **Stateless RS256 JWT** — auth signs; every service verifies with the public
  key, so auth downtime doesn't block authenticated requests.
- **Event-driven read-models** — the applications service checks apply-time
  eligibility against its *own* copies of job/candidate state (fed by Kafka), so
  it keeps accepting applications even when Jobs or Candidates is down.
- **Gateway circuit breakers** — a failing upstream trips only its own breaker
  (fast 503 on those routes); the gateway and other routes stay healthy.

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL · Alembic · Pydantic v2
· **Temporal** (job publishing) · **Kafka** (domain events) · Redis (rate limit)
· PyJWT (RS256) + Argon2 (pwdlib) · Docker Compose · uv · ruff · pytest.

## Run locally

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker.

```bash
# 1. Generate the dev RS256 keypair (writes keys/, gitignored)
./scripts/generate-keys.sh

# 2. Bring up everything: per-service DBs + Redis + Kafka + Temporal + services
docker compose up --build
#    Gateway → http://localhost:8080    Temporal UI → http://localhost:8088
```

Run services from source instead (faster iteration): start infra with
`docker compose up -d auth-db candidates-db jobs-db applications-db redis kafka temporal`,
apply each service's migrations (`cd services/<svc> && uv run alembic upgrade head`),
then run each with `uv run uvicorn app.main:app --port <port>` (and the jobs
worker with `uv run python -m app.worker`). See
[docs/microservices.md](docs/microservices.md) for the exact commands.

## Tests

```bash
uv sync --all-packages
uv run ruff check libs services
cd services/auth         && uv run pytest   # and candidates / jobs / applications / gateway
```

## Roadmap

| Week | Focus | Status |
| --- | --- | --- |
| 1 | Foundation + job/candidate management | ✅ (now a service) |
| 2 | Application workflow + Temporal publishing | ✅ (now services) |
| — | Microservices decomposition (fault isolation) | ✅ |
| 3 | Kafka events, background workers, observability | events ✅; workers/observability next |
| 4 | Embeddings + semantic search (GenAI) | planned (`search` service) |
| 5 | AI assistant + recommendations | planned (`ai-assistant` service) |
