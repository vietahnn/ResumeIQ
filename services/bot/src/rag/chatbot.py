import asyncio
import logging
from typing import Optional, AsyncIterator, Dict, Any, List
from sqlalchemy import select, func
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from services.shared.config import settings
from services.shared.database.session import async_session_factory
from services.shared.database.models import ChatMessage
from services.shared.llm import LLMService, get_langfuse_callback
from services.shared.schemas.events import AgentTaskType, AgentTaskRequestEvent
from services.shared.kafka import shared_producer
from services.shared.redis import push_working_memory, get_working_memory
from services.bot.src.tools import search_resume_cv, search_past_conversation

logger = logging.getLogger("AgenticChatbot")


class FastPathRAGChatbot:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()

    # Retrieves recent working context from Redis cache with PostgreSQL fallback
    async def _get_working_memory(self, session_id: str, limit: int = 4) -> str:
        cached_memory = await get_working_memory(session_id, limit=limit)
        if cached_memory:
            return cached_memory

        try:
            async with async_session_factory() as db:
                result = await db.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                    .order_by(ChatMessage.created_at.desc())
                    .limit(limit)
                )
                records = list(reversed(result.scalars().all()))
                if not records:
                    return ""

                turns: List[str] = []
                for r in records:
                    role_label = "Candidate" if r.role == "user" else "AI Advisor"
                    turns.append(f"{role_label}: {r.content}")
                    await push_working_memory(session_id, r.role, r.content)
                return "\n".join(turns)
        except Exception as err:
            logger.warning("Failed fetching working memory for session %s: %s", session_id, err)
            return ""

    # Persists chat turn into PostgreSQL history and updates Redis working memory
    async def save_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        try:
            async with async_session_factory() as db:
                msg = ChatMessage(
                    session_id=session_id,
                    role=role,
                    content=content,
                    extra_metadata=metadata
                )
                db.add(msg)
                await db.commit()
        except Exception as err:
            logger.error("Failed saving message to DB for session %s: %s", session_id, err)

        await push_working_memory(session_id=session_id, role=role, content=content, max_turns=6)

    # Dispatches consolidation event to Kafka every 20 completed user exchanges
    async def _check_and_trigger_consolidation(self, session_id: str, resume_id: Optional[str] = None) -> None:
        try:
            async with async_session_factory() as db:
                count_res = await db.execute(
                    select(func.count(ChatMessage.id))
                    .where(ChatMessage.session_id == session_id, ChatMessage.role == "user")
                )
                user_count = count_res.scalar() or 0

            if user_count > 0 and user_count % 20 == 0:
                task_event = AgentTaskRequestEvent(
                    task_id=f"cons_{session_id}_{user_count}",
                    session_id=session_id,
                    resume_id=resume_id,
                    task_type=AgentTaskType.CONSOLIDATE_MEMORY,
                    payload={"exchange_count": user_count}
                )
                asyncio.create_task(
                    shared_producer.send_event(settings.KAFKA_TOPIC_AGENT_TASKS, task_event)
                )
                logger.info("Triggered CONSOLIDATE_MEMORY event at exchange %d for session %s", user_count, session_id)
        except Exception as err:
            logger.warning("Failed checking consolidation trigger for session %s: %s", session_id, err)

    # Streams tokens dynamically invoking on-demand Qdrant tools for CV and past memory queries
    async def answer_stream(
        self,
        session_id: str,
        user_query: str,
        resume_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        await self.save_message(session_id=session_id, role="user", content=user_query, metadata={"resume_id": resume_id})

        working_memory = await self._get_working_memory(session_id, limit=4)
        lf_cb = get_langfuse_callback(session_id=session_id, trace_name="agentic_chat_stream")
        lf_config = {"callbacks": [lf_cb]} if lf_cb else None

        @tool
        def tool_search_resume(query: str) -> str:
            """Search detailed information, skills, experience, and projects from candidate resume."""
            if not resume_id:
                return "Candidate has not selected or uploaded a resume yet."
            return search_resume_cv(resume_id, query, limit=3)

        @tool
        def tool_search_past_memory(query: str) -> str:
            """Search past discussion points, career preferences, or summaries exchanged in prior turns."""
            return search_past_conversation(session_id, query, limit=2)

        tools = [tool_search_resume, tool_search_past_memory]
        tool_map = {t.name: t for t in tools}
        model_with_tools = self.llm.model.bind_tools(tools)

        system_prompt = (
            "You are ResumeIQ Career Assistant, an elite AI Career Advisor. "
            "Respond helpfully, politely, and professionally in Vietnamese.\n"
            "RULES:\n"
            "1. For general IT industry questions, answer directly using your knowledge without tools.\n"
            "2. If the user asks about their specific CV, skills, or projects, call `tool_search_resume`.\n"
            "3. If the user asks about past topics or agreements discussed earlier, call `tool_search_past_memory`.\n"
            "4. Use the recent Working Memory below to maintain continuity and resolve pronouns like 'nó', 'vị trí đó'."
        )

        messages = [SystemMessage(content=system_prompt)]
        if working_memory:
            messages.append(SystemMessage(content=f"--- RECENT CONVERSATION WORKING MEMORY ---\n{working_memory}"))
        messages.append(HumanMessage(content=user_query))

        full_response_parts: List[str] = []

        try:
            try:
                ai_msg = await asyncio.wait_for(model_with_tools.ainvoke(messages, config=lf_config), timeout=12.0)
            except (asyncio.TimeoutError, Exception) as tool_err:
                logger.warning("Tool calling ainvoke timed out or failed (%s). Falling back to direct model streaming...", tool_err)
                ai_msg = None

            if ai_msg and ai_msg.tool_calls:
                messages.append(ai_msg)
                for tool_call in ai_msg.tool_calls:
                    t_name = tool_call["name"]
                    t_args = tool_call["args"]
                    tool_func = tool_map.get(t_name)
                    if tool_func:
                        tool_res = tool_func.invoke(t_args)
                        messages.append(ToolMessage(content=str(tool_res), tool_call_id=tool_call["id"]))

                async for chunk in self.llm.model.astream(messages, config=lf_config):
                    text = chunk.content if hasattr(chunk, "content") else str(chunk)
                    if text:
                        full_response_parts.append(text)
                        yield text
            elif ai_msg:
                text_content = str(ai_msg.content)
                full_response_parts.append(text_content)
                words = text_content.split(" ")
                for i in range(0, len(words), 3):
                    chunk_text = " ".join(words[i:i+3]) + (" " if i+3 < len(words) else "")
                    yield chunk_text
                    await asyncio.sleep(0.015)
            else:
                async for chunk in self.llm.model.astream(messages, config=lf_config):
                    text = chunk.content if hasattr(chunk, "content") else str(chunk)
                    if text:
                        full_response_parts.append(text)
                        yield text

        except Exception as err:
            logger.error("Error during agentic stream execution: %s", err)
            fallback_err = f"An error occurred while generating response: {err}"
            full_response_parts.append(fallback_err)
            yield fallback_err

        final_answer = "".join(full_response_parts)
        await self.save_message(
            session_id=session_id,
            role="assistant",
            content=final_answer,
            metadata={"source": "agentic_rag", "resume_id": resume_id}
        )

        await self._check_and_trigger_consolidation(session_id, resume_id)


fast_path_chatbot = FastPathRAGChatbot()
