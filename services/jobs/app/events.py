"""Jobs service event publisher + a helper to emit job.upserted."""

from smarthire_common.events import (
    JOB_UPSERTED,
    TOPIC_JOB,
    EventEnvelope,
    KafkaEventPublisher,
)

from app.config import settings
from app.models import Job

publisher = KafkaEventPublisher(settings.kafka_bootstrap_servers)


def get_publisher() -> KafkaEventPublisher:
    return publisher


async def publish_job_upserted(pub: KafkaEventPublisher, job: Job) -> None:
    """Emit the job's id + status so consumers (applications) can track it."""
    await pub.publish(
        TOPIC_JOB,
        EventEnvelope(
            type=JOB_UPSERTED, data={"id": str(job.id), "status": job.status.value}
        ),
    )
