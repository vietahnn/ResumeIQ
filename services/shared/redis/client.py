import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
import redis.asyncio as aioredis
from services.shared.config import settings

logger = logging.getLogger("SharedRedisClient")

_redis_client: Optional[aioredis.Redis] = None


# Retrieves or initializes the shared async Redis connection client
def get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=10.0,
            socket_connect_timeout=10.0
        )
    return _redis_client


# Publishes a message dictionary to a specific session Pub/Sub channel
async def publish_to_session(session_id: str, message_data: Dict[str, Any]) -> int:
    client = get_redis_client()
    channel = f"{settings.REDIS_SESSION_CHANNEL_PREFIX}{session_id}"
    payload = json.dumps(message_data, default=str)
    return await client.publish(channel, payload)


# Subscribes to a session channel and yields incoming parsed JSON messages
async def subscribe_session(session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    client = get_redis_client()
    pubsub = client.pubsub()
    channel = f"{settings.REDIS_SESSION_CHANNEL_PREFIX}{session_id}"
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message and message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode("utf-8")
                try:
                    parsed = json.loads(data)
                    yield parsed
                except json.JSONDecodeError:
                    logger.warning("Failed to decode Redis pubsub JSON: %s", data)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


# Closes the shared async Redis client gracefully
async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
