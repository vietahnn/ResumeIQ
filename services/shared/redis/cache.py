import json
import hashlib
import logging
from typing import Dict, Any, Optional
from services.shared.redis.client import get_redis_client

logger = logging.getLogger("SharedRedisCache")

DEFAULT_CACHE_TTL = 7 * 24 * 3600


# Generates deterministic MD5 cache key based on resume, task type, and sorted payload
def generate_cache_key(
    resume_id: Optional[str],
    task_type: str,
    payload: Dict[str, Any]
) -> str:
    res_id = resume_id or "global"
    normalized_payload = json.dumps(payload, sort_keys=True, default=str)
    payload_hash = hashlib.md5(normalized_payload.encode("utf-8")).hexdigest()
    return f"cache:{res_id}:{task_type}:{payload_hash}"


# Retrieves cached outcome from Redis if available
async def get_cache(
    resume_id: Optional[str],
    task_type: str,
    payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    try:
        client = get_redis_client()
        key = generate_cache_key(resume_id, task_type, payload)
        raw_data = await client.get(key)
        if raw_data:
            return json.loads(raw_data)
        return None
    except Exception as err:
        logger.warning("Failed reading cache for key %s: %s", key if "key" in locals() else "unknown", err)
        return None


# Caches outcome into Redis with specified expiration time
async def set_cache(
    resume_id: Optional[str],
    task_type: str,
    payload: Dict[str, Any],
    result_data: Dict[str, Any],
    ttl: int = DEFAULT_CACHE_TTL
) -> None:
    try:
        client = get_redis_client()
        key = generate_cache_key(resume_id, task_type, payload)
        serialized_data = json.dumps(result_data, default=str)
        await client.set(key, serialized_data, ex=ttl)
    except Exception as err:
        logger.warning("Failed writing cache for key %s: %s", key if "key" in locals() else "unknown", err)


# Deletes all cache entries associated with a specific resume
async def invalidate_cache(resume_id: str) -> None:
    try:
        client = get_redis_client()
        pattern = f"cache:{resume_id}:*"
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
    except Exception as err:
        logger.warning("Failed invalidating cache for resume %s: %s", resume_id, err)
