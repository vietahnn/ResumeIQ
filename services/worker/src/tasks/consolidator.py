import json
import logging
import uuid
from typing import Dict, Any, Tuple
from sqlalchemy import select

from services.shared.llm import llm_service
from services.shared.database import async_session_factory, ChatMessage
from services.shared.vector import qdrant_service, embed_text
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

logger = logging.getLogger("MemoryConsolidatorTask")

CONSOLIDATOR_SYSTEM_PROMPT = (
    "You are an Elite AI Memory Consolidator for ResumeIQ. "
    "Your mission is to read the conversation history and existing summary, then produce:\n"
    "1. An updated, coherent conversation summary in Vietnamese (around 100-200 words) capturing the candidate's career direction, questions asked, and milestones reached.\n"
    "2. Extracted key candidate facts in JSON format.\n\n"
    "Respond in strictly valid JSON with this exact structure:\n"
    "{\n"
    '  "summary": "Đoạn tóm tắt diễn biến...",\n'
    '  "facts": {\n'
    '    "target_role": "Vị trí mong muốn...",\n'
    '    "target_salary": "Mức lương...",\n'
    '    "location_preference": "Địa điểm...",\n'
    '    "strengths": ["kỹ năng 1", "kỹ năng 2"],\n'
    '    "weaknesses": ["điểm yếu 1", "điểm yếu 2"],\n'
    '    "key_notes": "Ghi chú thêm..."\n'
    "  }\n"
    "}"
)


class MemoryConsolidatorTask:
    # Summarizes the latest 20 chat exchanges and upserts the vector summary into Qdrant conversation_summaries
    @classmethod
    async def execute(cls, payload: Dict[str, Any], session_id: str) -> Tuple[str, Dict[str, Any]]:
        if not session_id:
            logger.warning("Consolidation skipped: missing session_id")
            return "", {}

        logger.info("Starting memory consolidation for session: %s", session_id)

        existing_summary = ""
        dialogue_lines = []

        # 1. Fetch previous summary from Qdrant if available
        try:
            qdrant_service.init_collections()
            q_filter = Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))])
            dummy_vector = [0.0] * qdrant_service.vector_size
            past_results = qdrant_service.search_vectors(
                collection_name=qdrant_service.COLLECTION_CONVERSATION_SUMMARIES,
                query_vector=dummy_vector,
                limit=1,
                query_filter=q_filter
            )
            if past_results:
                existing_payload = getattr(past_results[0], "payload", {}) or {}
                existing_summary = existing_payload.get("content", "")
        except Exception as q_read_err:
            logger.debug("No prior summary found in Qdrant for session %s: %s", session_id, q_read_err)

        # 2. Fetch the latest 40 messages from PostgreSQL (equivalent to 20 Q&A exchanges)
        try:
            async with async_session_factory() as db:
                msg_result = await db.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                    .order_by(ChatMessage.created_at.desc())
                    .limit(40)
                )
                recent_messages = list(reversed(msg_result.scalars().all()))

                for msg in recent_messages:
                    sender = "Ứng viên" if msg.role == "user" else "AI Chuyên gia"
                    dialogue_lines.append(f"{sender}: {msg.content}")

        except Exception as db_err:
            logger.error("DB error fetching messages for consolidation in session %s: %s", session_id, db_err)
            return "", {}

        if not dialogue_lines:
            logger.info("No dialogue found to consolidate for session: %s", session_id)
            return "", {}

        prompt_parts = []
        if existing_summary:
            prompt_parts.append(f"=== BẢN TÓM TẮT TRƯỚC ĐÓ ===\n{existing_summary}\n")
        prompt_parts.append("=== 20 LƯỢT TRAO ĐỔI GẦN NHẤT ===\n" + "\n".join(dialogue_lines))
        prompt_parts.append("\nHãy tạo bản tóm tắt mới và trích xuất Facts đúng định dạng JSON.")

        full_prompt = "\n".join(prompt_parts)

        # 3. Invoke LLM to synthesize summary & extract facts
        new_summary = ""
        extracted_facts = {}
        try:
            raw_response = await llm_service.ainvoke(
                prompt=full_prompt,
                system_prompt=CONSOLIDATOR_SYSTEM_PROMPT
            )
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed_data = json.loads(cleaned)
            new_summary = parsed_data.get("summary", "")
            extracted_facts = parsed_data.get("facts", {})
        except Exception as llm_err:
            logger.warning("LLM consolidation parsing failed, using fallback summary: %s", llm_err)
            new_summary = f"Cuộc hội thoại gần nhất gồm {len(dialogue_lines)} tin nhắn trao đổi về tư vấn nghề nghiệp."
            extracted_facts = {}

        # 4. Upsert summary vector into dedicated Qdrant conversation_summaries collection
        try:
            summary_vector = embed_text(new_summary)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"summary_{session_id}"))
            point = PointStruct(
                id=point_id,
                vector=summary_vector,
                payload={
                    "session_id": session_id,
                    "content": new_summary,
                    "facts": extracted_facts,
                    "total_messages_consolidated": len(dialogue_lines)
                }
            )
            qdrant_service.upsert_vectors(
                collection_name=qdrant_service.COLLECTION_CONVERSATION_SUMMARIES,
                points=[point]
            )
            logger.info("Upserted summary vector to Qdrant conversation_summaries for session: %s", session_id)
        except Exception as qdrant_err:
            logger.warning("Failed indexing summary vector to Qdrant: %s", qdrant_err)

        return new_summary, extracted_facts
