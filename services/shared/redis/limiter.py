import logging
from typing import Tuple
from services.shared.redis.client import get_redis_client

logger = logging.getLogger("SharedRedisLimiter")

DEFAULT_WINDOW_SECONDS = 60


# Evaluates atomic sliding counter rate limit returning allowed status, remaining quota, and retry delay
async def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int = DEFAULT_WINDOW_SECONDS
) -> Tuple[bool, int, int]:
    try:
        client = get_redis_client()
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        results = await pipe.execute()
        current_count = int(results[0])
        current_ttl = int(results[1])

        if current_count == 1 or current_ttl == -1:
            await client.expire(key, window_seconds)
            current_ttl = window_seconds

        if current_count > limit:
            retry_after = max(current_ttl, 1)
            return False, 0, retry_after

        remaining = max(limit - current_count, 0)
        return True, remaining, max(current_ttl, 0)

    except Exception as err:
        logger.warning("Rate limit check failed for key %s (failing open): %s", key, err)
        return True, limit, 0
