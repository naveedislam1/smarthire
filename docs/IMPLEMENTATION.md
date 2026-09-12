# SmartHire — Implementation Guide (Week 1)

A file-by-file explanation of **every component** built in Week 1: what it does,
the key classes/functions it defines, what it depends on, and *why it exists*.
Read [architecture.md](architecture.md) first for the big picture.

## Table of contents

1. [Overview & request flow](#1-overview--request-flow)
2. [Config & tooling](#2-config--tooling)
3. [Core (`app/core`)](#3-core-appcore)
4. [Common (`app/common`)](#4-common-appcommon)
5. [Jobs module (`app/jobs`)](#5-jobs-module-appjobs)
6. [Candidates module (`app/candidates`)](#6-candidates-module-appcandidates)
7. [App wiring (`app/main.py`)](#7-app-wiring-appmainpy)
8. [Migrations (`migrations/`)](#8-migrations-migrations)
9. [Tests (`tests/`)](#9-tests-tests)
10. [Data model reference](#10-data-model-reference)
11. [API reference](#11-api-reference)

---

## 1. Overview & request flow

A request travels through four layers; each has one job:

```
HTTP → router → service → repository → PostgreSQL
                  │
                  └─ raises domain error → exception handler → JSON response
```

- **router** — declares the endpoint, validates input via Pydantic, wires up the
  service through FastAPI dependency injection, sets status codes.
- **service** — the business brain: state transitions, uniqueness rules,
  existence checks. Raises framework-agnostic domain exceptions.
- **repository** — the only code that runs SQL. Returns ORM objects or `None`.
- **models** — SQLAlchemy 2.0 typed table definitions.

The layers are split so each can be tested and changed independently, and so
Week 2+ can wrap services in workflows/events without touching data access.

---

## 2. Config & tooling

### `pyproject.toml`
Project metadata, runtime dependencies (FastAPI, SQLAlchemy async, asyncpg,
Alembic, Pydantic v2, pydantic-settings), a `dev` dependency group (pytest,
pytest-asyncio, httpx, aiosqlite, ruff, mypy), and tool config for ruff, pytest
(`asyncio_mode = "auto"`), and mypy. Uses the hatchling build backend with
`packages = ["app"]`. *Why:* one declarative, lockable source of truth for deps
and tooling — the uv "best practice" setup.

### `.python-version`
Pins Python `3.12` so `uv` provisions the right interpreter. *Why:* reproducible
builds across machines.

### `docker-compose.yml`
Defines a `db` service (Postgres 16, healthcheck, named volume) and an optional
`api` service behind the `api` profile. *Why:* one command to get a local
Postgres; the API can run on the host (fast reload) or fully containerised.

### `Dockerfile`
Multi-stage uv-based build: a `builder` stage installs deps into a venv, a slim
`runtime` stage runs uvicorn. *Why:* small, reproducible production image.

### `.env.example`
Documents every environment variable (app, database URL, logging) with safe
local defaults and no secrets. Copied to `.env` for local runs. *Why:*
onboarding + explicit configuration contract.

### `alembic.ini`
Alembic config pointing at `migrations/`. The DB URL is intentionally blank —
it's injected at runtime from app settings (see `migrations/env.py`). *Why:* one
DB URL source (settings), not two.

### `.gitignore` / `.dockerignore`
Keep caches, virtualenvs, and `.env` out of git and the build context.

---

## 3. Core (`app/core`)

### `config.py`
Defines `Settings` (a `pydantic_settings.BaseSettings`) with typed fields for
app metadata, `database_url`, API prefix, and logging. `get_settings()` is
`lru_cache`d so it's built once; `settings` is the shared instance. *Depends on:*
pydantic-settings. *Why:* typed, validated, environment-driven config used by
the app, Alembic, and tests alike.

### `database.py`
- `Base` — the `DeclarativeBase` every model inherits.
- `engine` — the async engine created from `settings.database_url`.
- `SessionFactory` — `async_sessionmaker` with `expire_on_commit=False`.
- `get_db()` — an async-generator FastAPI dependency yielding one session per
  request and closing it afterwards.

*Why:* centralises all DB plumbing; `get_db` is the single seam the tests
override to inject a test database.

### `logging.py`
`configure_logging()` sets root + uvicorn log levels/format from settings;
`get_logger(name)` returns a module logger. *Why:* one logging setup now, a
single-file upgrade path to OpenTelemetry in Week 3.

### `exceptions.py`
- `SmartHireError` (base) with `NotFoundError` (404), `ConflictError` (409),
  `ValidationError` (422) subclasses, each carrying a `status_code` + `detail`.
- `register_exception_handlers(app)` attaches one handler that renders any
  `SmartHireError` as `{"detail": ...}` with its status code.

*Why:* services stay HTTP-agnostic; error responses are consistent everywhere.

---

## 4. Common (`app/common`)

### `enums.py`
`JobStatus` (`draft`, `published`, `processing`, `ready`) and `EmploymentType`
as `StrEnum`s. `processing`/`ready` are defined now (used in Week 2) so the DB
enum type is stable. *Why:* shared, type-safe vocabularies.

### `models.py`
`UUIDMixin` (UUID primary key, `default=uuid4`) and `TimestampMixin`
(`created_at`/`updated_at` with server defaults + `onupdate`). *Why:* every
table needs these; define once, reuse.

### `pagination.py`
`PaginationParams` (validated `limit`/`offset` query params) and `Page[T]` —
a generic response model (`items`, `total`, `limit`, `offset`). *Why:* uniform
list responses across all list endpoints.

---

## 5. Jobs module (`app/jobs`)

### `models.py`
`Job` ORM model (`jobs` table): `title`, `description`, `location`,
`employment_type`, `required_skills`/`hiring_stages` (JSON list — `JSONB` on
Postgres via `JSONList = JSON().with_variant(JSONB(), "postgresql")`),
`status` (indexed enum, defaults to `DRAFT`), and nullable `recruiter_id`.
Inherits `UUIDMixin`/`TimestampMixin`. *Why:* the durable shape of a job posting.

### `schemas.py`
Pydantic models: `JobCreate` (create payload), `JobUpdate` (all-optional partial
update), `JobRead` (`from_attributes=True`, adds `id`/`status`/timestamps).
Field constraints (e.g. non-empty title) live here. *Why:* validated,
explicit API contracts decoupled from the ORM.

### `repository.py`
`JobRepository(session)` — `create`, `get`, `list` (with optional status filter
+ total count), `update`, `delete`. Pure data access, no rules. *Why:* isolates
all job SQL in one place.

### `service.py`
`JobService(repository)` — `create_job` (forces `DRAFT`), `get_job`,
`list_jobs`, `update_job` (applies only sent fields via
`model_dump(exclude_unset=True)`), `publish_job` (the Week-1 posting flow:
`DRAFT → PUBLISHED`, rejects invalid transitions with `ValidationError`),
`delete_job`, and a private `_get_or_404`. *Why:* the business rules for jobs.

### `router.py`
Declares the `/jobs` routes and the `get_job_service` dependency that wires
`JobRepository(db) → JobService`. Maps HTTP verbs to service methods and sets
status codes (201 create, 204 delete). *Why:* the HTTP surface for jobs.

---

## 6. Candidates module (`app/candidates`)

### `models.py`
`Candidate` (`candidates`): unique-indexed `email`, `full_name`, `phone`, and a
1:1 `profile` relationship (`uselist=False`, `cascade="all, delete-orphan"`,
`lazy="selectin"`). `CandidateProfile` (`candidate_profiles`): unique FK
`candidate_id` (cascade delete), `headline`, `skills` (JSON list),
`experience_years`, `resume_url`, `bio`. *Why:* a candidate plus optional
extended profile, with the DB enforcing the one-to-one and cleanup.

### `schemas.py`
`CandidateCreate`/`CandidateUpdate`, `CandidateProfileUpsert`/
`CandidateProfileRead`, and `CandidateRead` (embeds the optional profile).
`email` uses `EmailStr` for format validation. *Why:* API contracts for
candidates and profiles.

### `repository.py`
`CandidateRepository(session)` — `create`, `get`, `get_by_email` (for the
duplicate check), `list` + count, `save`, `delete`, and `get_profile`. *Why:*
all candidate/profile SQL in one place.

### `service.py`
`CandidateService(repository)` — `register_candidate` (409 on duplicate email),
`get_candidate`, `list_candidates`, `update_candidate`, `delete_candidate`, and
profile ops `upsert_profile` (create-or-update the single profile) /
`get_profile` (404 if none yet). *Why:* candidate business rules, including the
uniqueness rule surfaced as a clean 409 rather than a DB IntegrityError.

### `router.py`
Declares the `/candidates` routes (including `/{id}/profile` GET + PUT) and the
`get_candidate_service` dependency. *Why:* the HTTP surface for candidates.

---

## 7. App wiring (`app/main.py`)

- `lifespan` — configures logging on startup, disposes the engine on shutdown.
- `create_app()` — the application factory: builds `FastAPI`, registers the
  exception handlers, includes the jobs and candidates routers under
  `settings.api_v1_prefix`, and defines `/` (service metadata) and `/health`.
- `app = create_app()` — the ASGI entry point uvicorn runs.

*Why:* a factory makes the app trivially re-buildable per test with overridden
dependencies, and keeps wiring in one readable place.

---

## 8. Migrations (`migrations/`)

### `env.py`
Async Alembic environment. Imports the model modules so their tables register on
`Base.metadata`, injects `settings.database_url` into Alembic config, and runs
migrations through the async engine (`run_migrations_online`) or offline. *Why:*
`--autogenerate` and `upgrade` work against the same async DB the app uses.

### `script.py.mako`
Template for generated revision files (modern typing syntax). *Why:* consistent,
lint-clean migration scaffolding.

### `versions/*_init_jobs_and_candidates.py`
The autogenerated initial migration creating `jobs`, `candidates`,
`candidate_profiles`, their enum types, and indexes. *Why:* the versioned,
reproducible schema baseline.

---

## 9. Tests (`tests/`)

### `conftest.py`
Fixtures: `db_session` builds a fresh in-memory SQLite schema per test via
`Base.metadata.create_all`; `client` builds the app with `get_db` overridden to
that session and returns an httpx `AsyncClient` over the ASGI app. *Why:* fast,
isolated, service-free tests that still exercise the real routers/services/ORM
(portable JSON columns make the same models work on SQLite).

### `jobs/test_jobs_api.py`
Covers create-as-draft, get/list, update, the publish flow (including the 422 on
re-publish and status filtering), delete, and 404. *Why:* locks the job
lifecycle and error paths.

### `candidates/test_candidates_api.py`
Covers register, 409 duplicate email, profile upsert + get (including 404 before
a profile exists and idempotent re-upsert), update, delete, and 404. *Why:*
locks candidate + profile behaviour.

---

## 10. Data model reference

**`jobs`**

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | PK |
| `title` | varchar(255) | required |
| `description` | text | required |
| `location` | varchar(255) | nullable |
| `employment_type` | enum | default `full_time` |
| `required_skills` | JSONB/JSON | list of strings |
| `hiring_stages` | JSONB/JSON | ordered list of stage names |
| `status` | enum | `draft`→`published`(→`processing`→`ready`), indexed |
| `recruiter_id` | UUID | nullable (no auth yet) |
| `created_at`/`updated_at` | timestamptz | server-managed |

**`candidates`**

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | PK |
| `email` | varchar(320) | unique, indexed |
| `full_name` | varchar(255) | required |
| `phone` | varchar(50) | nullable |
| `created_at`/`updated_at` | timestamptz | server-managed |

**`candidate_profiles`** (1:1 with `candidates`)

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | PK |
| `candidate_id` | UUID | unique FK → `candidates.id`, cascade delete |
| `headline` | varchar(255) | nullable |
| `skills` | JSONB/JSON | list of strings |
| `experience_years` | int | nullable, 0–80 |
| `resume_url` | varchar(1024) | nullable |
| `bio` | text | nullable |
| `created_at`/`updated_at` | timestamptz | server-managed |

---

## 11. API reference

Base prefix: `/api/v1`.

| Method | Path | Body | Success | Errors | Rule |
| --- | --- | --- | --- | --- | --- |
| POST | `/jobs` | `JobCreate` | 201 `JobRead` | 422 | Created as `draft` |
| GET | `/jobs` | — | 200 `Page[JobRead]` | — | `limit`/`offset`/`status_filter` |
| GET | `/jobs/{id}` | — | 200 `JobRead` | 404 | — |
| PATCH | `/jobs/{id}` | `JobUpdate` | 200 `JobRead` | 404, 422 | Partial update |
| POST | `/jobs/{id}/publish` | — | 200 `JobRead` | 404, 422 | Only `draft` may publish |
| DELETE | `/jobs/{id}` | — | 204 | 404 | — |
| POST | `/candidates` | `CandidateCreate` | 201 `CandidateRead` | 409, 422 | Unique email |
| GET | `/candidates` | — | 200 `Page[CandidateRead]` | — | `limit`/`offset` |
| GET | `/candidates/{id}` | — | 200 `CandidateRead` | 404 | Includes profile |
| PATCH | `/candidates/{id}` | `CandidateUpdate` | 200 `CandidateRead` | 404 | Partial update |
| DELETE | `/candidates/{id}` | — | 204 | 404 | Cascades to profile |
| PUT | `/candidates/{id}/profile` | `CandidateProfileUpsert` | 200 `CandidateProfileRead` | 404 | Create or update |
| GET | `/candidates/{id}/profile` | — | 200 `CandidateProfileRead` | 404 | 404 if no profile |
| GET | `/health` | — | 200 | — | Liveness |
| GET | `/` | — | 200 | — | Service metadata |
