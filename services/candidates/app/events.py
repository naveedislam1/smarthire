"""Candidates service event publisher (module-level, started at lifespan)."""

from smarthire_common.events import KafkaEventPublisher

from app.config import settings

publisher = KafkaEventPublisher(settings.kafka_bootstrap_servers)


def get_publisher() -> KafkaEventPublisher:
    return publisher
