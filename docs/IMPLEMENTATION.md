# SmartHire — Implementation Guide

A file-by-file reference for the microservices codebase: what each component does,
its key classes/functions, and why it exists. Read
[architecture.md](architecture.md) first for the big picture and
[microservices.md](microservices.md) for how to run and verify it.

## Table of contents

1. [Shared library (`libs/smarthire_common`)](#1-shared-library-libssmarthire_common)
2. [Auth service (`services/auth`)](#2-auth-service-servicesauth)
3. [Candidates service (`services/candidates`)](#3-candidates-service-servicescandidates)
4. [Jobs service (`services/jobs`)](#4-jobs-service-servicesjobs)
5. [Applications service (`services/applications`)](#5-applications-service-servicesapplications)
6. [Gateway service (`services/gateway`)](#6-gateway-service-servicesgateway)
7. [Data model per service](#7-data-model-per-service)
8. [Event reference](#8-event-reference)
9. [API reference (via gateway)](#9-api-reference-via-gateway)
10. [Tests](#10-tests)

Every service shares the same shape: `app/config.py` (settings), `app/database.py`
(engine/session/`get_db` from the shared factories), `app/models.py` (ORM),
`app/schemas.py` (Pydantic), `app/repository.py` (SQL), `app/service.py` (rules),
`app/dependencies.py` (DI + `build_security`), `app/router.py` (HTTP), `app/main.py`
(factory + `/health` + `/ready`), plus `migrations/`, `tests/`, `Dockerfile`,
`pyproject.toml` (`package = false`, depends on `smarthire-common`).

---

## 1. Shared library (`libs/smarthire_common`)

The one installed package; every service imports from it.

- **`config.py`** — `BaseServiceSettings` (pydantic-settings): service identity,
  `api_v1_prefix`, log level, and JWT config with `public_key_pem()` /
  `private_key_pem()` helpers (inline PEM or file path). Services subclass it and
  add their own `database_url`.
- **`database.py`** — `Base` (DeclarativeBase) + `make_engine` /
  `make_session_factory` / `make_get_db` factories. Each service builds its own
  engine from its own URL.
- **`security.py`** — the crypto seam: Argon2 `hash_password`/`verify_password`;
  RS256 `create_access_token`/`create_refresh_token`/`decode_token`;
  `CurrentIdentity` (user_id + role from a verified token); and
  `build_security(public_key, algorithm, token_url)` → a `Security` bundle with
  `oauth2_scheme`, `get_current_identity`, and `require_role(*roles)`. This is the
  centralised auth reused by every service.
- **`events/__init__.py`** — the Kafka layer: `EventEnvelope`
  (`event_id`/`type`/`occurred_at`/`data`); topic constants (`TOPIC_JOB`,
  `TOPIC_CANDIDATE`, `TOPIC_APPLICATION`) and type constants (`JOB_UPSERTED`,
  `CANDIDATE_UPSERTED`, `APPLICATION_CREATED`, …); `KafkaEventPublisher`
  (fail-soft aiokafka producer with `start`/`stop`/`publish`); and `run_consumer`
  (an auto-reconnecting consumer loop that dispatches envelopes to a handler).
- **`enums.py`** — `Role` (recruiter/candidate), shared for RBAC.
- **`models.py`** — `UUIDMixin`, `TimestampMixin`.
- **`pagination.py`** — `PaginationParams`, generic `Page[T]`.
- **`exceptions.py`** — `SmartHireError` + `NotFound`/`Conflict`/`Validation`/
  `Auth`/`Forbidden` subclasses and `register_exception_handlers`.
- **`logging.py`** — `configure_logging`, `get_logger`.

---

## 2. Auth service (`services/auth`)

Owns users; the only signer of JWTs.

- **`models.py`** — `User` (email unique, `hashed_password` Argon2, `full_name`,
  `role`, `is_active`).
- **`schemas.py`** — `RegisterRequest`, `UserRead` (never exposes the hash),
  `TokenResponse`, `RefreshRequest`.
- **`security` usage** — signs with `settings.private_key_pem()`; other services
  only verify.
- **`service.py`** — `AuthService`: `register` (409 on duplicate email),
  `login` (verify → issue access+refresh), `refresh` (validate a *refresh* token →
  new tokens). Generic error text avoids leaking which emails exist.
- **`router.py`** — `/auth/register`, `/auth/login` (OAuth2 form),
  `/auth/refresh`, `/auth/me` (verifies the access token, loads the user from
  auth-db).
- **`dependencies.py`** — builds `security` from the public key and wires the
  service.

---

## 3. Candidates service (`services/candidates`)

- **`models.py`** — `Candidate` (email unique) + one-to-one `CandidateProfile`
  (skills JSON, experience, resume_url, bio; cascade delete).
- **`service.py`** — `register_candidate` (409 duplicate email), get/list/update/
  delete, and profile upsert/get. Publishes `candidate.upserted` on create/update
  and `candidate.deleted` on delete (so the applications read-model stays current).
- **`events.py`** — a `KafkaEventPublisher` + `publish_candidate_*` helpers.
- **`router.py`** — `/candidates` CRUD + `/{id}/profile`; login required; listing
  the candidate pool requires the recruiter role.

---

## 4. Jobs service (`services/jobs`)

Owns jobs and runs the Temporal publishing workflow.

- **`models.py`** — `Job` (title, description, employment_type, `required_skills`,
  `hiring_stages`, `status`, `recruiter_id` as a plain UUID, plus
  `structured_content` and `extracted_keywords` filled by the workflow).
- **`service.py`** — `JobService`: create/get/list/update/delete and
  `request_publish` (validates, sets `processing`). Publishes `job.upserted` /
  `job.deleted`.
- **`events.py`** — publisher + `publish_job_upserted(publisher, job)` helper used
  by both the API and the workflow activities.
- **`publishing/`**
  - `content.py` — pure heuristics: `breakdown_description`, `extract_skills`,
    `extract_keywords` (no I/O, no GenAI).
  - `constants.py` — workflow + activity names (dependency-free for the sandbox).
  - `activities.py` — idempotent DB-writing steps: `breakdown_job`,
    `extract_job_skills_keywords`, `mark_job_ready`, `mark_job_failed`
    (the last two also emit `job.upserted`).
  - `workflows.py` — `JobPublishingWorkflow`: breakdown → extract → mark_ready,
    each retried; on failure → mark_failed then raise.
  - `temporal_client.py` — `JobPublisher` protocol + `TemporalPublisher` +
    `get_temporal_publisher` (tests substitute a fake).
- **`worker.py`** — runnable Temporal worker (`python -m app.worker`); registers
  the workflow + activities and starts the event publisher.
- **`router.py`** — `/jobs` CRUD; writes require recruiter; `POST /{id}/publish`
  sets `processing`, starts the workflow, returns **202**.

---

## 5. Applications service (`services/applications`)

The apply workflow + the cross-service read-models — the heart of the
fault-isolation design.

- **`enums.py`** — `ApplicationStatus`, `ACTIVE_APPLICATION_STATUSES`, and the
  `APPLICATION_TRANSITIONS` state machine.
- **`models.py`** — `Application` (`UNIQUE(job_id, candidate_id)`, `status`,
  `stage_history`, `applied_at`; job/candidate ids are plain UUIDs) plus the
  read-models **`JobRef`** (id + status) and **`CandidateRef`** (id).
- **`repository.py`** — application CRUD + `get_for_pair` (duplicate),
  `count_active_for_candidate` (limit), and read-model getters.
- **`service.py`** — `ApplicationService`: `apply` (eligibility via read-models →
  duplicate/idempotency → limit → create), `advance_stage` (validated), `withdraw`.
  Publishes `application.*`.
- **`consumers.py`** — `handle_event` upserts/deletes `JobRef`/`CandidateRef` from
  `job.*`/`candidate.*`; `run_read_model_consumer` runs the Kafka loop.
- **`main.py`** — starts the read-model consumer as a background task in the app
  lifespan (so the service keeps its read-models current).
- **`router.py`** — `/applications`; apply/withdraw are candidate-only, stage
  changes recruiter-only; reads the `Idempotency-Key` header.

---

## 6. Gateway service (`services/gateway`)

- **`config.py`** — upstream URLs (auth/candidates/jobs/applications), timeouts,
  breaker thresholds, Redis + rate-limit settings.
- **`circuit.py`** — `AsyncCircuitBreaker` (closed → open after N failures →
  half-open after cooldown) + `CircuitOpenError`. Self-contained, predictable.
- **`proxy.py`** — `Upstream` (base URL + its own breaker) and `forward`, which
  relays method/headers/body/query via a shared `httpx` client, wrapped in the
  breaker; returns a clean **503** on breaker-open or connection/timeout.
- **`ratelimit.py`** — Redis fixed-window limiter that **fails open**.
- **`main.py`** — `/health` (independent of upstreams) + a single catch-all under
  `/api/v1/{full_path}` that selects the upstream by the first segment, rate-limits
  by client IP, and forwards.

---

## 7. Data model per service

**auth.users** — id · email (unique) · hashed_password (Argon2) · full_name ·
role (enum) · is_active · timestamps.

**candidates.candidates** — id · email (unique) · full_name · phone · timestamps.
**candidates.candidate_profiles** (1:1) — id · candidate_id (unique FK, cascade) ·
headline · skills (JSON) · experience_years · resume_url · bio · timestamps.

**jobs.jobs** — id · title · description · location · employment_type (enum) ·
required_skills (JSON) · hiring_stages (JSON) · status (`draft`→`processing`→
`ready`/`failed`; also `published`) · structured_content (JSON) ·
extracted_keywords (JSON) · recruiter_id (UUID, no FK) · timestamps.

**applications.applications** — id · job_id (UUID) · candidate_id (UUID) ·
status (enum) · stage_history (JSON) · applied_at · timestamps ·
**UNIQUE(job_id, candidate_id)**.
**applications.job_refs** (read-model) — id · status.
**applications.candidate_refs** (read-model) — id.

No cross-service foreign keys: services own their own data; links are UUIDs.

---

## 8. Event reference

| Topic | Type | Producer | Consumer → effect |
| --- | --- | --- | --- |
| `candidate-events` | `candidate.upserted` / `candidate.deleted` | candidates | applications → upsert/delete `CandidateRef` |
| `job-events` | `job.upserted` (id, status) / `job.deleted` | jobs | applications → upsert/delete `JobRef` |
| `application-events` | `application.created` / `application.stage_changed` / `application.withdrawn` | applications | (future: notifications, scoring, analytics) |

Envelope: `{event_id, type, occurred_at, data}`. Consumers dedupe by id
(idempotent). Producer/consumer are fail-soft.

---

## 9. API reference (via gateway)

Base: `http://localhost:8080/api/v1`. Access: **Public** / **Auth** (any logged-in
user) / **Recruiter** / **Candidate**.

| Method | Path | Access | Notes |
| --- | --- | --- | --- |
| POST | `/auth/register` | Public | 201; 409 duplicate |
| POST | `/auth/login` | Public | form `username`/`password` → tokens |
| POST | `/auth/refresh` | Public | refresh token → new access |
| GET | `/auth/me` | Auth | current user |
| POST | `/candidates` | Auth | register candidate; 409 duplicate |
| GET | `/candidates` | Recruiter | list pool |
| GET/PATCH/DELETE | `/candidates/{id}` | Auth | |
| PUT/GET | `/candidates/{id}/profile` | Auth | |
| POST | `/jobs` | Recruiter | created `draft` |
| GET | `/jobs` (+`status_filter`) · `/jobs/{id}` | Auth | |
| PATCH/DELETE | `/jobs/{id}` | Recruiter | |
| POST | `/jobs/{id}/publish` | Recruiter | **202**; async `processing → ready` |
| POST | `/applications` | Candidate | apply; `Idempotency-Key` supported; 409 duplicate, 422 eligibility/limit |
| GET | `/applications` (+filters) · `/applications/{id}` | Auth | |
| PATCH | `/applications/{id}/stage` | Recruiter | validated transition |
| POST | `/applications/{id}/withdraw` | Candidate | |
| GET | `/health` (each service; gateway too) | Public | liveness |
| GET | `/ready` (each service) | Public | dependency check |

Unauthenticated → 401; wrong role → 403; a down upstream → 503 at the gateway.

---

## 10. Tests

Each service has `tests/` run with `uv run pytest` from the service directory
(RS256 keypair generated in-process, in-memory SQLite, fakes for Kafka/Temporal):

- **auth** (5) — register/login/me, duplicate 409, wrong password 401, refresh +
  type guard, `/me` needs a token.
- **candidates** (5) — register, duplicate 409, profile upsert/get, update/delete,
  authz (401/403).
- **jobs** (9) — create-as-draft, publish starts the workflow (202 + fake
  publisher), authz, 404, plus pure `content` helpers and Temporal workflow
  orchestration (time-skipping env, happy path + failure→mark_failed).
- **applications** (9) — apply against seeded read-models, duplicate 409,
  idempotent retry, eligibility 422, limit 422, stage transitions, authz, and the
  read-model consumer (`handle_event`) upsert/delete.
- **gateway** (4) — `/health` independent of upstreams, dead upstream → 503,
  breaker opens after repeated failures, and unit tests of the breaker.
