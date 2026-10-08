import json
import logging
from typing import List, Optional
from services.shared.redis.client import get_redis_client

logger = logging.getLogger("RedisWorkingMemory")

KEY_PREFIX_WORKING_MEMORY = "session:{session_id}:memory"


# Appends a recent chat turn to Redis list and trims older items to maintain sliding window
async def push_working_memory(
    session_id: str,
    role: str,
    content: str,
    max_turns: int = 6,
    ttl: int = 86400
) -> None:
    try:
        client = get_redis_client()
        key = KEY_PREFIX_WORKING_MEMORY.format(session_id=session_id)
        payload = json.dumps({"role": role, "content": content}, ensure_ascii=False)

        pipe = client.pipeline()
        pipe.lpush(key, payload)
        pipe.ltrim(key, 0, max_turns - 1)
        pipe.expire(key, ttl)
        await pipe.execute()
    except Exception as err:
        logger.warning("Failed pushing working memory to Redis for session %s: %s", session_id, err)


# Fetches and formats the latest turns from Redis list in chronological order
async def get_working_memory(session_id: str, limit: int = 4) -> str:
    try:
        client = get_redis_client()
        key = KEY_PREFIX_WORKING_MEMORY.format(session_id=session_id)
        raw_items = await client.lrange(key, 0, limit - 1)
        if not raw_items:
            return ""

        formatted_turns: List[str] = []
        for item in reversed(raw_items):
            try:
                turn = json.loads(item)
                role_label = "Candidate" if turn.get("role") == "user" else "AI Advisor"
                formatted_turns.append(f"{role_label}: {turn.get('content', '')}")
            except json.JSONDecodeError:
                continue

        return "\n".join(formatted_turns)
    except Exception as err:
        logger.warning("Failed fetching working memory from Redis for session %s: %s", session_id, err)
        return ""


# Clears cached working memory for a session
async def clear_working_memory(session_id: str) -> None:
    try:
        client = get_redis_client()
        key = KEY_PREFIX_WORKING_MEMORY.format(session_id=session_id)
        await client.delete(key)
    except Exception as err:
        logger.warning("Failed clearing working memory for session %s: %s", session_id, err)
