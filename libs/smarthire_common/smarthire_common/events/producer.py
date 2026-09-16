"""Fail-soft Kafka event publisher.

A Kafka outage must not break the owning service, so publish failures are logged
and swallowed (the API still succeeds). Hardening to a transactional outbox is a
follow-up; for now state is committed to the service DB first, then the event is
emitted best-effort.
"""

from aiokafka import AIOKafkaProducer

from smarthire_common.events import EventEnvelope
from smarthire_common.logging import get_logger

logger = get_logger(__name__)


class KafkaEventPublisher:
    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap)
        try:
            await self._producer.start()
            logger.info("Kafka producer connected to %s", self._bootstrap)
        except Exception as exc:  # broker not up yet — stay fail-soft
            logger.warning("Kafka producer could not start: %s", exc)
            self._producer = None

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(self, topic: str, envelope: EventEnvelope) -> None:
        if self._producer is None:
            logger.warning("Kafka unavailable; dropped event %s", envelope.type)
            return
        try:
            await self._producer.send_and_wait(
                topic, envelope.model_dump_json().encode()
            )
        except Exception as exc:
            logger.warning("Failed to publish %s: %s", envelope.type, exc)
