# SmartHire — Week 2 Implementation Guide (Step by Step)

> **Historical (superseded).** This walks through how the Week 2 features were
> first built in the **monolith**. The system has since been split into
> microservices and the monolith removed — see [architecture.md](architecture.md),
> [microservices.md](microservices.md), and [IMPLEMENTATION.md](IMPLEMENTATION.md)
> for the current structure. Kept for traceability. File paths below (e.g.
> `app/applications/*`) refer to the old monolith layout.

This document walks through **how Week 2 was built**, step by step, and explains
the *why* behind each decision. It complements:
- [week-2-plan.md](week-2-plan.md) — the plan we executed
- [architecture.md](architecture.md) — the design & workflow diagrams
- [IMPLEMENTATION.md](IMPLEMENTATION.md) — the per-file reference for the whole app

**What Week 2 delivered:** a candidate **application workflow** (duplicate
handling, eligibility, application limits, idempotency, stage tracking) and a
**Temporal-orchestrated job publishing pipeline** (`processing → ready`, with
content breakdown + skill/keyword extraction and partial-failure safety).

---

## Step 1 — Extend the shared vocabulary (enums)

**File:** `app/common/enums.py`

We started from the shared enums so every layer speaks the same language.

1. Added `JobStatus.FAILED` — the publishing workflow needs a terminal "could not
   complete" state so a half-processed job is never left looking `ready`.
2. Added `ApplicationStatus` (`applied → screening → interview → offer → hired`,
   plus `rejected`, `withdrawn`).
3. Added two lookup tables next to the enum:
   - `ACTIVE_APPLICATION_STATUSES` — which statuses count toward a candidate's
     limit (everything except the terminal ones).
   - `APPLICATION_TRANSITIONS` — a map of `status → allowed next statuses`. This
     makes the state machine **data**, so the service validates a transition with
     a single lookup instead of scattered `if` checks.

*Why first:* both the applications module and the publishing workflow depend on
these; defining them once avoids duplication and keeps the state machine in one
readable place.

## Step 2 — Configuration knobs

**File:** `app/core/config.py`

Added typed settings (all overridable via environment):
- `max_active_applications` (default 10) — the application-limit rule.
- `temporal_host`, `temporal_namespace`, `temporal_task_queue` — where the
  publishing workflow runs.

*Why:* rules and infrastructure endpoints belong in settings, not hard-coded, so
tests and deployments can change them without touching logic.

## Step 3 — New Job columns for structured content

**Files:** `app/jobs/models.py`, `app/jobs/schemas.py`

1. Added `structured_content` (JSON map) and `extracted_keywords` (JSON list) to
   the `Job` model. Reused the `JSONB`-on-Postgres / `JSON`-elsewhere variant
   pattern so tests still run on SQLite.
2. Exposed both fields on `JobRead` so API clients can see the workflow output.

*Why:* the publishing workflow needs somewhere to persist what it computes; the
recruiter's manually entered `required_skills` gets **merged** with auto-extracted
skills (see Step 7), not overwritten.

## Step 4 — The Applications domain module

**Files:** `app/applications/{models,schemas,repository,service,router}.py`

Built as a vertical slice, identical in shape to `jobs`/`candidates`.

### 4a. Model (`models.py`)
- `Application` with FKs `job_id → jobs.id` and `candidate_id → candidates.id`
  (both `ON DELETE CASCADE`).
- **`UniqueConstraint(job_id, candidate_id)`** — duplicate handling enforced by
  the database, not just application code.
- `stage_history` (JSON list of `{status, at}`) — the audit trail that makes an
  application **trackable** end to end.

### 4b. Repository (`repository.py`)
Pure data access: `create`, `get`, `get_for_pair` (for the duplicate check),
`count_active_for_candidate` (for the limit), a filtered `list`, and `save`.

### 4c. Service (`service.py`) — the business rules
`apply()` runs the rules **in a deliberate order**:
1. **Eligibility** — candidate must exist; job must exist **and** be
   `published`/`ready`. Otherwise `422`.
2. **Duplicate handling** — if an application already exists for this
   `(job, candidate)`: return it unchanged when the request carried an
   `Idempotency-Key` (a safe retry), else `409`.
3. **Application limit** — count non-terminal applications; `422` if at the cap.
4. Create the application as `applied` with the first `stage_history` entry.

Also: `advance_stage()` validates the move against `APPLICATION_TRANSITIONS`
(`422` on an illegal jump) and appends to history; `withdraw()` moves a
non-terminal application to `withdrawn`.

### 4d. Router (`router.py`) — HTTP + access control
- Router-level `Depends(get_current_user)` (all routes need login).
- `POST /applications` → **candidate** role; reads the optional `Idempotency-Key`
  header.
- `GET /applications` (+filters) and `GET /applications/{id}` → any authenticated
  user.
- `PATCH /applications/{id}/stage` → **recruiter** role.
- `POST /applications/{id}/withdraw` → **candidate** role.

*Why this shape:* it reuses Week 1's centralised `require_role` guard, so access
control is declared, not reimplemented.

## Step 5 — Pure content processing (no Temporal, no DB, no GenAI)

**File:** `app/publishing/content.py`

Three deterministic functions:
- `breakdown_description()` → buckets description lines into
  `requirements / responsibilities / benefits` by detecting section headings.
- `extract_skills()` → matches a known-skills dictionary against the text.
- `extract_keywords()` → frequency-ranked keywords minus stopwords.

*Why pure:* keeping the logic free of I/O makes it trivially unit-testable and
safe to call from Temporal activities. **This is heuristic on purpose** — GenAI
extraction is Part B (Weeks 4–5).

## Step 6 — Temporal building blocks

**Files:** `app/publishing/{constants,activities,workflows,worker,publisher}.py`

### 6a. `constants.py`
Just the workflow name and activity names. Kept dependency-free so the workflow
module can import it inside Temporal's deterministic sandbox without pulling in
SQLAlchemy.

### 6b. `activities.py` — the side-effecting steps
Four activities, each opening its own DB session:
- `breakdown_job` → compute + persist `structured_content`.
- `extract_job_skills_keywords` → compute skills+keywords, **merge** skills with
  the recruiter's, persist.
- `mark_job_ready` → set status `ready`.
- `mark_job_failed` → set status `failed` (compensation).

Each activity is **idempotent** (recompute + overwrite) so Temporal can retry it
without double-processing — a core requirement from the brief.

### 6c. `workflows.py` — the orchestration
`JobPublishingWorkflow.run(job_id)`:
```
breakdown → extract → mark_ready        (each retried up to 3×)
        └── on failure → mark_failed, then re-raise
```
*Why:* Temporal guarantees each step runs to completion or is retried; the
`try/except → mark_failed` means a partial failure ends as `failed`, **never** a
half-written `ready` ("partial failures must not corrupt the pipeline").

### 6d. `worker.py` — the process that runs it
Connects to Temporal, registers the workflow + activities on the task queue.
**Key detail learned during integration:** the worker must import *all* model
modules, not just `jobs`, so SQLAlchemy can resolve cross-table foreign keys
(e.g. `jobs.recruiter_id → users.id`) when an activity writes. Run it with:
```
uv run python -m app.publishing.worker
```

### 6e. `publisher.py` — starting the workflow from the API
A tiny `JobPublisher` protocol with a `TemporalPublisher` implementation and a
`get_publisher()` FastAPI dependency. **Why a protocol:** the API depends on the
abstraction, so tests substitute a fake that records calls instead of needing a
live Temporal server.

## Step 7 — Rewire the publish endpoint

**Files:** `app/jobs/service.py`, `app/jobs/router.py`

- `JobService.publish_job` became `request_publish`: it validates (only `draft`
  or `failed` may publish — the latter enables retry), sets status `processing`,
  and commits.
- The router's `POST /jobs/{id}/publish` now: calls `request_publish`, then
  `await publisher.start(job_id)`, and returns **`202 Accepted`** with the job in
  `processing`. Publishing is asynchronous; the client polls (or watches the
  Temporal UI) for `ready`.

*Why 202:* the response acknowledges the request while the actual work continues
in the background — the correct semantics for a long-running, non-blocking job.

## Step 8 — Wiring & infrastructure

- `app/main.py` → registered the applications router.
- `migrations/env.py` → imported `app.applications.models` for autogenerate.
- `docker-compose.yml` → added `temporal` (`temporalio/auto-setup`, reusing the
  shared Postgres) and `temporal-ui` (http://localhost:8080).
- `pyproject.toml` → added `temporalio`.

## Step 9 — Database migration

Regenerated the Alembic migration on a clean schema. It creates the
`applications` table (+ its unique constraint and indexes), the new `jobs`
columns, and the `application_status` enum, alongside the existing tables.
```
uv run alembic revision --autogenerate -m "week2 applications and publishing columns"
uv run alembic upgrade head
```

## Step 10 — Tests

- `tests/publishing/test_content.py` — unit tests for the pure helpers.
- `tests/publishing/test_workflow.py` — orchestration tests using Temporal's
  **time-skipping** `WorkflowEnvironment` with **stand-in activities** (no DB):
  verifies the happy-path ordering and the failure→`mark_failed` compensation.
- `tests/applications/test_applications_api.py` — duplicate (409), idempotent
  retry, eligibility (422), limit (422, via `monkeypatch`), stage transitions,
  withdraw, and authz (401/403).
- `tests/conftest.py` — added a `FakePublisher` and override so the publish
  endpoint never contacts Temporal in tests; a `db_session` helper forces a job
  to `ready` for application tests.
- Updated the jobs publish test to expect `202` + `processing` and to assert the
  publisher was invoked.

**Result:** 34 tests passing, `ruff` clean.

## Step 11 — End-to-end verification (real Temporal)

1. `docker compose up -d db temporal temporal-ui`
2. `uv run alembic upgrade head`
3. `uv run python -m app.publishing.worker` (separate terminal)
4. `uv run uvicorn app.main:app` and exercise the API.

Observed: a published job moved `processing → ready`; `required_skills` became
`[python, fastapi, postgresql, kafka, docker]`, keywords were populated, and the
description split into requirements/responsibilities/benefits. The application
flow returned `applied → 409 duplicate → idempotent same id → screening → 403 for
candidate → 422 invalid jump`, exactly as designed.

---

## How to run Week 2 locally (quick reference)

```bash
# 1. Start Postgres + Temporal + Temporal UI
docker compose up -d db temporal temporal-ui

# 2. Apply the schema
uv run alembic upgrade head

# 3. Start the Temporal worker (leave running)
uv run python -m app.publishing.worker

# 4. Start the API
uv run uvicorn app.main:app --reload

# Temporal Web UI: http://localhost:8080   ·   API docs: http://localhost:8000/docs
```
