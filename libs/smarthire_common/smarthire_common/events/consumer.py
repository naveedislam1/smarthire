"""Kafka consumer loop with automatic reconnect.

If the broker is unavailable the loop retries with backoff instead of crashing —
so a consumer can start before Kafka is ready and catch up once it is.
"""

import asyncio
from collections.abc import Awaitable, Callable

from aiokafka import AIOKafkaConsumer

from smarthire_common.events import EventEnvelope
from smarthire_common.logging import get_logger

logger = get_logger(__name__)

Handler = Callable[[EventEnvelope], Awaitable[None]]


async def run_consumer(
    *,
    bootstrap_servers: str,
    topics: list[str],
    group_id: str,
    handler: Handler,
) -> None:
    while True:
        consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        try:
            await consumer.start()
        except Exception as exc:
            logger.warning("Consumer '%s' cannot reach Kafka (%s); retrying…", group_id, exc)
            await consumer.stop()
            await asyncio.sleep(3)
            continue

        logger.info("Consumer '%s' subscribed to %s", group_id, topics)
        try:
            async for msg in consumer:
                try:
                    envelope = EventEnvelope.model_validate_json(msg.value)
                    await handler(envelope)
                except Exception as exc:  # a bad message must not kill the loop
                    logger.exception("Handler error for a message: %s", exc)
        except Exception as exc:
            logger.warning("Consumer '%s' dropped (%s); reconnecting…", group_id, exc)
        finally:
            await consumer.stop()
        await asyncio.sleep(1)
