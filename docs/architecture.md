# SmartHire — Architecture (Week 1)

This document covers the high-level design, data/flow, key decisions, and the
assumptions/tradeoffs made for the Week 1 foundation. For a file-by-file
walkthrough of the code, see [IMPLEMENTATION.md](IMPLEMENTATION.md).

## 1. Scope of Week 1

Week 1 delivers the **foundation + core management** slice of Part A:

- Domain-modular service structure
- Relational schema for **jobs**, **candidates**, and **candidate profiles**
- CRUD APIs for jobs and candidates + candidate profile management
- A **basic job posting flow** (`draft → published`)
- Local environment (uv, Docker Compose Postgres, Alembic migrations)

Intentionally **deferred** to later milestones (scaffolded but not built):
Temporal publishing workflow and candidate applications (Week 2); Kafka events,
Celery/RabbitMQ workers, and observability stack (Week 3); the GenAI semantic
and assistant layers (Weeks 4–5).

## 2. Component / layer view

Each domain module (`app/jobs`, `app/candidates`) is a vertical slice with the
same four layers:

```
router      → HTTP surface: request/response models, status codes, DI wiring
service     → business rules, state transitions, orchestration
repository  → async data access (SQLAlchemy); no business logic
models      → ORM tables (SQLAlchemy 2.0 typed mappings)
```

Cross-cutting concerns live in `app/core` (config, database, logging,
exceptions) and `app/common` (shared mixins, enums, pagination). This gives the
"clear separation of concerns between domain components" the brief asks for, and
means new domains (applications, interviews, analytics) are added by dropping in
a new folder — not by editing shared files.

## 3. Request/data flow

```
Client ──HTTP──▶ router ──▶ service ──▶ repository ──▶ AsyncSession ──▶ PostgreSQL
                   ▲            │
                   │            └── raises SmartHireError (NotFound/Conflict/Validation)
                   └────────────── exception handler maps error → JSON + status code
```

- A FastAPI dependency (`get_db`) yields one `AsyncSession` per request.
- The router builds the service (`repository(session)` → `service(repository)`).
- The service enforces rules and raises domain exceptions; a single registered
  handler renders them as consistent JSON (`{"detail": ...}`) with the right code.

## 4. Data model

| Table | Purpose | Notable columns |
| --- | --- | --- |
| `jobs` | Job postings | `status` (enum), `required_skills`/`hiring_stages` (JSON list), `recruiter_id` (nullable UUID) |
| `candidates` | Applicants | `email` (unique, indexed), `full_name`, `phone` |
| `candidate_profiles` | 1:1 profile | `candidate_id` (unique FK, cascade delete), `skills` (JSON list), `experience_years`, `resume_url`, `bio` |

All tables carry a UUID primary key and `created_at`/`updated_at` timestamps via
shared mixins. JSON columns use `JSONB` on PostgreSQL and portable `JSON`
elsewhere (so tests can run on in-memory SQLite).

## 5. Key design decisions

- **Domain-modular over layered.** The system grows into many domains
  (applications, interviews, analytics, AI assistant). Vertical slices keep each
  domain cohesive and independently evolvable.
- **Async end-to-end.** FastAPI + SQLAlchemy async + asyncpg, because the brief
  centres on high load during hiring spikes; an async stack is the right base.
- **Repository/service split.** Keeps SQL out of business logic and business
  logic out of HTTP handlers, which makes the code testable and lets Week 2 wrap
  services in Temporal activities without rewriting data access.
- **Framework-agnostic domain errors.** Services raise `NotFoundError` /
  `ConflictError` / `ValidationError`; only the API layer knows about HTTP.
- **Alembic from day one.** Schema changes are versioned and reproducible rather
  than auto-created at startup.
- **uv + pyproject.** Fast, reproducible dependency management with a lockfile.

## 6. Assumptions & tradeoffs

- **No authentication yet.** Not in any Week 1 deliverable. `recruiter_id` is a
  nullable opaque UUID on `jobs`; real recruiter/candidate accounts and auth
  arrive later. Tradeoff: endpoints are currently unauthenticated.
- **NoSQL DB deferred.** The overall stack lists a NoSQL store, but Week 1's
  data is naturally relational. NoSQL is introduced when analytics/unstructured
  data lands (Week 3+).
- **Skills entered manually.** `required_skills` is supplied by the recruiter
  this week; automatic skill/keyword extraction is a Week 2 deliverable.
- **Offset pagination.** Simple and sufficient now; can move to keyset
  pagination if large-list performance demands it.
- **Basic publish flow.** `draft → published` is a direct transition this week;
  Week 2 replaces it with the Temporal `processing → ready` lifecycle.

## 7. How later weeks plug in

- **Week 2:** an `applications` domain module (same 4-layer shape); the
  `publish_job` service becomes the trigger for a Temporal workflow.
- **Week 3:** services emit domain events to Kafka; Celery workers consume them
  for scoring/notifications/analytics; OpenTelemetry wraps the layers.
- **Weeks 4–5:** job/candidate text is embedded into a vector DB; a LangGraph
  assistant reads the same repositories for retrieval.
