# SmartHire — Intelligent Workforce Orchestration & Recruitment Platform

Backend for **SmartHire**, TalentSphere Inc.'s recruitment automation platform.
This repository is built incrementally over 5 weekly milestones.

> **Status: Week 1 — Foundation + Core Management.**
> Job & candidate management (CRUD), candidate profiles, and a basic job
> posting flow, on a clean domain-modular FastAPI + async PostgreSQL foundation.

---

## Project overview

SmartHire solves manual, slow, and inconsistent hiring workflows with a
scalable, event-driven backend. Week 1 lays the foundation: a well-structured
service, a relational schema for jobs and candidates, and the core management
APIs — everything later milestones (Temporal workflows, Kafka events, GenAI
assistant) build on.

## Architecture

Domain-modular layout. Each domain (`jobs`, `candidates`) owns its own
router → service → repository → model, so HTTP, business rules, and persistence
stay cleanly separated.

```
              HTTP request
                   │
        ┌──────────▼──────────┐
        │   router (FastAPI)  │  validation, status codes
        └──────────┬──────────┘
        ┌──────────▼──────────┐
        │      service        │  business rules, state transitions
        └──────────┬──────────┘
        ┌──────────▼──────────┐
        │     repository      │  async SQLAlchemy data access
        └──────────┬──────────┘
        ┌──────────▼──────────┐
        │  PostgreSQL (async) │
        └─────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for design decisions and
[docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) for a file-by-file walkthrough.

## Setup instructions

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker (for Postgres).

```bash
# 1. Install dependencies
uv sync

# 2. Start PostgreSQL
docker compose up -d db

# 3. Configure environment
cp .env.example .env

# 4. Apply the database schema
uv run alembic upgrade head

# 5. Run the API (http://localhost:8000, docs at /docs)
uv run uvicorn app.main:app --reload
```

Run the whole stack (API + DB) in containers instead:

```bash
docker compose --profile api up --build
```

Run the tests (no external services needed — uses in-memory SQLite):

```bash
uv run pytest
uv run ruff check .
```

## API overview

All endpoints are under `/api/v1`. Interactive docs at `/docs` (use the
**Authorize** button with a token from `/auth/login`).

### Authentication

JWT bearer auth (OAuth2 password flow) with two roles: **recruiter** and
**candidate**. Log in to get an access + refresh token, then send
`Authorization: Bearer <access_token>` on every request. See
[docs/architecture.md](docs/architecture.md#8-authentication--authorization).

| Method | Path | Description | Access |
| --- | --- | --- | --- |
| POST | `/auth/register` | Create an account (`role`: recruiter/candidate) | Public |
| POST | `/auth/login` | Get access + refresh tokens (form: `username`,`password`) | Public |
| POST | `/auth/refresh` | Exchange a refresh token for a new access token | Public |
| GET | `/auth/me` | Current user | Authenticated |
| POST | `/jobs` | Create a job (starts in `draft`) | Recruiter |
| GET | `/jobs` | List jobs (pagination, `status_filter`) | Authenticated |
| GET | `/jobs/{id}` | Retrieve a job | Authenticated |
| PATCH | `/jobs/{id}` | Update job fields | Recruiter |
| POST | `/jobs/{id}/publish` | Publish: `draft` → `published` | Recruiter |
| DELETE | `/jobs/{id}` | Delete a job | Recruiter |
| POST | `/candidates` | Register a candidate | Authenticated |
| GET | `/candidates` | List candidates (pagination) | Recruiter |
| GET | `/candidates/{id}` | Retrieve a candidate (+ profile) | Authenticated |
| PATCH | `/candidates/{id}` | Update a candidate | Authenticated |
| DELETE | `/candidates/{id}` | Delete a candidate | Authenticated |
| PUT | `/candidates/{id}/profile` | Create/update profile | Authenticated |
| GET | `/candidates/{id}/profile` | Retrieve profile | Authenticated |
| GET | `/health` | Liveness check | Public |

## Tech stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.12 |
| Web framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 (asyncpg driver) |
| Migrations | Alembic (async) |
| Validation | Pydantic v2 |
| Auth | OAuth2 password flow, JWT (PyJWT), Argon2 (pwdlib), RBAC |
| Tooling | uv, ruff, mypy, pytest |
| Local infra | Docker Compose |

Later milestones add Temporal, Kafka + Schema Registry, Celery + RabbitMQ,
Redis, Prometheus/Grafana/Jaeger/OpenTelemetry, and the GenAI layer
(LangGraph + vector DB).

## Roadmap

| Week | Focus |
| --- | --- |
| **1 (this)** | Foundation + core job/candidate management |
| 2 | Application workflow + Temporal publishing pipeline |
| 3 | Kafka events, background workers, observability |
| 4 | Embeddings + semantic search (GenAI) |
| 5 | AI recruiter/candidate assistant |
