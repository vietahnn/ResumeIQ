import asyncio
import logging
from typing import Optional
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from services.shared.redis import subscribe_session
from services.shared.database.session import async_session_factory
from services.shared.database.models import ChatMessage

logger = logging.getLogger("RedisSessionListener")


# Continuously listens to the Redis session Pub/Sub channel and forwards results to the client WebSocket
async def listen_session_and_forward(session_id: str, websocket: WebSocket) -> None:
    try:
        async for message in subscribe_session(session_id):
            if "type" not in message:
                message["type"] = "status"
            try:
                await websocket.send_json(message)
            except Exception as send_err:
                logger.warning("Failed forwarding message to WebSocket for session %s: %s", session_id, send_err)
                break

            # Persists the completed worker agent response into PostgreSQL chat history
            if message.get("status") == "SUCCESS" and message.get("content"):
                try:
                    async with async_session_factory() as db:
                        chat_record = ChatMessage(
                            session_id=session_id,
                            role="assistant",
                            content=message["content"],
                            extra_metadata=message.get("metadata")
                        )
                        db.add(chat_record)
                        await db.commit()
                except Exception as db_err:
                    logger.error("Failed saving assistant chat message to DB: %s", db_err)
    except asyncio.CancelledError:
        logger.debug("Redis listener task cancelled for session: %s", session_id)
    except Exception as err:
        logger.error("Unexpected error in Redis session listener for session %s: %s", session_id, err)
