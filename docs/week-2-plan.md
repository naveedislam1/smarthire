# SmartHire — Week 2 Plan: Application Workflow + Publishing Pipeline

> **Historical (superseded).** This is the original plan for the Week 2 features
> as built in the earlier **monolith**. Those features now run as microservices —
> see [architecture.md](architecture.md) and [microservices.md](microservices.md)
> for the current system. Kept for traceability of how the work progressed.

## Context

Week 1 delivered the foundation (jobs & candidates CRUD, profiles, auth, a basic
`draft → published` flow). **Week 2** adds the two workflow-heavy pieces from the
brief:

1. **Candidate application workflow** — duplicate handling, eligibility checks,
   application limits, idempotency, and application tracking (stage transitions).
2. **Job publishing workflow (Temporal)** — replace the direct publish with an
   orchestrated **`processing → ready`** lifecycle that breaks the job
   description into components and extracts skills/keywords, where **partial
   failures never corrupt the pipeline**.

**Deliverables:** application workflow working reliably · publishing workflow
orchestrated via Temporal · job state transitions handled.

**Decisions:** real **Temporal** (server + worker via docker-compose, `temporalio`
SDK). Content breakdown/skill extraction is **heuristic (no GenAI)** — GenAI is
Part B (Weeks 4–5). Builds on Week 1's domain-modular structure and auth.

## 1. Applications domain (`app/applications/`)

Same `router → service → repository → models` shape as existing modules.

**Model — `Application`**
- `id` (UUID), `job_id` FK→`jobs.id`, `candidate_id` FK→`candidates.id`
- **`UNIQUE(job_id, candidate_id)`** → DB-level duplicate protection
- `status` enum, `current_stage`, `stage_history` (JSONB timeline), `applied_at`,
  timestamps

**Status lifecycle** (`app/common/enums.py`)
- `applied → screening → interview → offer → hired`, plus `rejected`,
  `withdrawn`. Each transition appends to `stage_history` for tracking.

**Business rules (service)**
- **Duplicate** → 409 (unique violation surfaced as `ConflictError`).
- **Eligibility** → job must be `ready`/`published`; candidate must exist; 422 otherwise.
- **Application limit** → cap active applications per candidate
  (`settings.max_active_applications`), 422 when exceeded.
- **Idempotency** → `Idempotency-Key` header on `POST /applications` dedupes
  retried submissions.

**Endpoints** (`/api/v1/applications`)
- `POST /applications` — candidate applies (candidate role)
- `GET /applications` — recruiter: all (filter by job/status); candidate: own
- `GET /applications/{id}` — owner or recruiter
- `PATCH /applications/{id}/stage` — advance stage (recruiter role)
- `POST /applications/{id}/withdraw` — candidate withdraws own

## 2. Job Publishing Workflow (Temporal)

Replaces direct `draft → published` in `app/jobs/service.py::publish_job`.

**Infra**
- `docker-compose.yml`: add `temporal` (`temporalio/auto-setup`) + Temporal Web UI.
- `pyproject.toml`: add `temporalio`.
- Settings: `temporal_host`, `temporal_namespace`, `temporal_task_queue`.

**New package `app/publishing/`**
- `client.py` — connect to Temporal.
- `worker.py` — runnable worker (`uv run python -m app.publishing.worker`).
- `workflows.py` — `JobPublishingWorkflow`.
- `activities.py` — the steps below.

**Lifecycle**
1. `POST /jobs/{id}/publish` → set status **`processing`**, start workflow, return
   immediately (non-blocking).
2. Workflow runs activities (each retriable — Temporal handles partial failure):
   - `breakdown_description` → requirements / responsibilities / benefits
     (heuristic section parsing).
   - `extract_keywords_skills` → naive keyword/skill extraction.
   - `persist_structured_data` → write to new `Job` columns.
   - `mark_ready` → status **`ready`** only after all steps succeed.
3. On failure the job stays `processing`/`failed` — never a half-written `ready`.

**New `Job` columns** (migration): `structured_content` (JSONB), `extracted_keywords`
(JSONB). `required_skills` becomes workflow-populated (was manual in Week 1).

## 3. Migrations, tests, docs

- **Alembic**: `applications` table + new `jobs` columns + application enums.
- **Tests**: application rules (duplicate 409, eligibility 422, limit 422,
  idempotent retry), stage transitions; publishing via Temporal
  `WorkflowEnvironment` (time-skipping) + activity unit tests. Keep SQLite-in-memory.
- **Docs**: `architecture.md` (workflow/event-flow section + Temporal diagram),
  `IMPLEMENTATION.md` (applications + publishing walkthroughs), README API table,
  Postman collection.

## Key files

- **New:** `app/applications/*`, `app/publishing/*`, migration, tests, doc updates
- **Modified:** `app/jobs/service.py` (publish → start workflow),
  `app/jobs/models.py` (+columns), `app/common/enums.py` (application enums),
  `docker-compose.yml`, `pyproject.toml`, `app/core/config.py`

## Verification

`docker compose up -d db temporal` → run the worker → `uv run alembic upgrade head`
→ publish a job, watch `processing → ready` in the Temporal Web UI → apply as a
candidate (confirm duplicate/eligibility/limit rules) → advance stages as a
recruiter → `uv run pytest` green, `uv run ruff check .` clean.

## Out of scope (later weeks)

Kafka events, Celery workers, notifications, analytics pipeline, and full
observability are **Week 3**. GenAI skill extraction / semantic indexing is
**Part B (Weeks 4–5)**. Week 2's extraction is deliberately heuristic.
