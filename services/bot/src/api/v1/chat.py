import asyncio
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy import select, func, desc, delete

from services.bot.src.websocket.connection_manager import ws_manager
from services.bot.src.dispatcher.task_dispatcher import task_dispatcher
from services.bot.src.pubsub.redis_listener import listen_session_and_forward
from services.bot.src.rag.chatbot import fast_path_chatbot
from services.shared.database.session import async_session_factory
from services.shared.database.models import ChatMessage
from services.shared.redis import get_cache, check_rate_limit, clear_working_memory

logger = logging.getLogger("BotChatRouter")
router = APIRouter()


# Handles real-time bi-directional chat communication with Fast-Path RAG and Kafka task dispatching
@router.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(session_id, websocket)
    redis_task = asyncio.create_task(listen_session_and_forward(session_id, websocket))

    try:
        while True:
            data = await websocket.receive_json()
            query = data.get("query", "").strip()
            resume_id = data.get("resume_id")
            target_jd = data.get("target_jd")
            explicit_task = data.get("task_type")

            if not query:
                continue

            is_allowed, remaining, retry_after = await check_rate_limit(
                key=f"ratelimit:chat:{session_id}",
                limit=20,
                window_seconds=60
            )
            if not is_allowed:
                await websocket.send_json({
                    "type": "error",
                    "code": "RATE_LIMITED",
                    "message": f"You are sending messages too quickly. Please wait {retry_after} seconds before trying again.",
                    "retry_after": retry_after
                })
                continue

            heavy_task_type = task_dispatcher.detect_heavy_task(query, explicit_task)

            if heavy_task_type:
                await fast_path_chatbot.save_message(
                    session_id=session_id,
                    role="user",
                    content=query,
                    metadata={"target_jd": target_jd, "resume_id": resume_id}
                )

                payload = {
                    "user_query": query,
                    "target_jd": target_jd,
                    "resume_id": resume_id
                }

                cached_result = await get_cache(resume_id, heavy_task_type.value, payload)
                if cached_result:
                    logger.info(
                        "\n%s\n"
                        "⚡⚡⚡ [REDIS CACHE HIT] Fast-Path Triggered! ⚡⚡⚡\n"
                        "   • Task Type : %s\n"
                        "   • Resume ID : %s\n"
                        "   • Latency   : ~5ms (0 LLM Tokens, Kafka Bypassed)\n"
                        "%s",
                        "=" * 60,
                        heavy_task_type.value,
                        resume_id,
                        "=" * 60
                    )
                    cached_content = cached_result.get("content", "")
                    cached_metadata = {**cached_result.get("metadata", {}), "source": "cache"}
                    await websocket.send_json({
                        "type": "status",
                        "task_id": f"cached_{session_id}",
                        "session_id": session_id,
                        "status": "SUCCESS",
                        "task_type": heavy_task_type.value,
                        "content": cached_content,
                        "metadata": cached_metadata
                    })
                    await fast_path_chatbot.save_message(
                        session_id=session_id,
                        role="assistant",
                        content=cached_content,
                        metadata=cached_metadata
                    )
                    continue

                logger.info("[REDIS CACHE MISS] Heavy task %s dispatched to Worker via Kafka...", heavy_task_type.value)
                await websocket.send_json({
                    "type": "status",
                    "status": "DISPATCHED",
                    "task_type": heavy_task_type.value,
                    "message": f"Task {heavy_task_type.value} dispatched to Worker pool via Kafka..."
                })

                await task_dispatcher.dispatch_task(
                    session_id=session_id,
                    task_type=heavy_task_type,
                    resume_id=resume_id,
                    payload=payload
                )
            else:
                await websocket.send_json({"type": "stream_start"})
                async for chunk in fast_path_chatbot.answer_stream(
                    session_id=session_id,
                    user_query=query,
                    resume_id=resume_id
                ):
                    await websocket.send_json({"type": "chunk", "content": chunk})
                await websocket.send_json({"type": "stream_end"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session: %s", session_id)
    except Exception as err:
        logger.error("Error in websocket session %s: %s", session_id, err)
    finally:
        redis_task.cancel()
        ws_manager.disconnect(session_id, websocket)


# Fetches stored conversation turns for a specific session from PostgreSQL
@router.get("/history/{session_id}", response_model=List[Dict[str, Any]])
async def get_chat_history(session_id: str):
    async with async_session_factory() as db:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        records = result.scalars().all()

        return [
            {
                "id": r.id,
                "role": r.role,
                "content": r.content,
                "extra_metadata": r.extra_metadata,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ]


# Lists past chat sessions with summaries, titles, and resume context
@router.get("/sessions", response_model=List[Dict[str, Any]])
async def list_chat_sessions():
    async with async_session_factory() as db:
        summary_query = (
            select(
                ChatMessage.session_id,
                func.count(ChatMessage.id).label("message_count"),
                func.max(ChatMessage.created_at).label("last_active_at")
            )
            .group_by(ChatMessage.session_id)
            .order_by(desc("last_active_at"))
            .limit(50)
        )
        summary_res = await db.execute(summary_query)
        summaries = summary_res.all()

        if not summaries:
            return []

        session_ids = [row.session_id for row in summaries]

        first_msgs_query = (
            select(ChatMessage.session_id, ChatMessage.content, ChatMessage.extra_metadata)
            .where(
                ChatMessage.session_id.in_(session_ids),
                ChatMessage.role == "user"
            )
            .order_by(ChatMessage.created_at.asc())
        )
        first_msgs_res = await db.execute(first_msgs_query)
        first_msgs = first_msgs_res.all()

        first_msg_map: Dict[str, str] = {}
        resume_id_map: Dict[str, Optional[str]] = {}
        for msg in first_msgs:
            if msg.session_id not in first_msg_map:
                first_msg_map[msg.session_id] = msg.content
            if msg.session_id not in resume_id_map and msg.extra_metadata and isinstance(msg.extra_metadata, dict):
                r_id = msg.extra_metadata.get("resume_id")
                if r_id:
                    resume_id_map[msg.session_id] = r_id

        results = []
        for row in summaries:
            raw_title = first_msg_map.get(row.session_id)
            if raw_title:
                clean_title = raw_title.strip().replace("\n", " ")
                title = (clean_title[:38] + "...") if len(clean_title) > 38 else clean_title
            else:
                title = f"Conversation {row.session_id[:8]}"

            results.append({
                "session_id": row.session_id,
                "title": title,
                "message_count": row.message_count,
                "last_active_at": row.last_active_at.isoformat() if row.last_active_at else None,
                "resume_id": resume_id_map.get(row.session_id)
            })

        return results


# Deletes an entire chat session from PostgreSQL and clears its working memory in Redis
@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    async with async_session_factory() as db:
        await db.execute(
            delete(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        await db.commit()

    await clear_working_memory(session_id)
    return {"status": "success", "session_id": session_id, "message": "Session deleted"}
