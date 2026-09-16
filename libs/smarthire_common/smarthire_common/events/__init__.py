"""Event contracts + Kafka producer/consumer shared across services.

Topics are one-per-domain; the specific event is named by ``EventEnvelope.type``
(e.g. ``job.upserted``). Consumers dedupe/act idempotently, and both producer and
consumer are **fail-soft** — a Kafka outage degrades eventing, it never crashes
the owning service (fault isolation).
"""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

# --- Topics (one per producing domain) ---
TOPIC_CANDIDATE = "candidate-events"
TOPIC_JOB = "job-events"
TOPIC_APPLICATION = "application-events"

# --- Event type names ---
CANDIDATE_UPSERTED = "candidate.upserted"
CANDIDATE_DELETED = "candidate.deleted"
JOB_UPSERTED = "job.upserted"          # carries {id, status}
JOB_DELETED = "job.deleted"
APPLICATION_CREATED = "application.created"
APPLICATION_STAGE_CHANGED = "application.stage_changed"
APPLICATION_WITHDRAWN = "application.withdrawn"


class EventEnvelope(BaseModel):
    """Common wrapper for every domain event.

    ``event_id`` enables idempotent consumers; ``type`` names the event; ``data``
    carries the domain payload.
    """

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    type: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data: dict


from smarthire_common.events.consumer import run_consumer  # noqa: E402
from smarthire_common.events.producer import KafkaEventPublisher  # noqa: E402

__all__ = [
    "EventEnvelope",
    "KafkaEventPublisher",
    "run_consumer",
    "TOPIC_CANDIDATE",
    "TOPIC_JOB",
    "TOPIC_APPLICATION",
    "CANDIDATE_UPSERTED",
    "CANDIDATE_DELETED",
    "JOB_UPSERTED",
    "JOB_DELETED",
    "APPLICATION_CREATED",
    "APPLICATION_STAGE_CHANGED",
    "APPLICATION_WITHDRAWN",
]
