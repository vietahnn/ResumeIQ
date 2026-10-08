import logging
from typing import Optional, List
from qdrant_client.models import Filter, FieldCondition, MatchValue

from services.shared.vector import qdrant_service, embed_text

logger = logging.getLogger("BotMemoryTools")


# Searches Qdrant for semantic resume chunks matching the candidate query
def search_resume_cv(resume_id: str, query: str, limit: int = 3) -> str:
    if not resume_id or not query:
        return ""

    try:
        query_vector = embed_text(query[:1000])
        q_filter = Filter(must=[FieldCondition(key="resume_id", match=MatchValue(value=resume_id))])
        results = qdrant_service.search_vectors(
            collection_name=qdrant_service.COLLECTION_RESUMES,
            query_vector=query_vector,
            limit=limit,
            query_filter=q_filter
        )

        chunks: List[str] = []
        for res in results:
            payload = getattr(res, "payload", {}) or {}
            content = payload.get("content")
            section = payload.get("section", "detail")
            if content:
                chunks.append(f"[{section.upper()}]: {content}")

        return "\n\n".join(chunks)
    except Exception as err:
        logger.warning("Error querying resume CV context from Qdrant: %s", err)
        return ""


# Searches past conversation summaries in Qdrant applying a relevance threshold
def search_past_conversation(
    session_id: str,
    query: str,
    limit: int = 2,
    score_threshold: float = 0.70
) -> str:
    if not session_id or not query:
        return ""

    try:
        query_vector = embed_text(query[:1000])
        q_filter = Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))])
        results = qdrant_service.search_vectors(
            collection_name=qdrant_service.COLLECTION_CONVERSATION_SUMMARIES,
            query_vector=query_vector,
            limit=limit,
            query_filter=q_filter
        )

        matches: List[str] = []
        for res in results:
            score = getattr(res, "score", 0.0)
            if score < score_threshold:
                continue

            payload = getattr(res, "payload", {}) or {}
            content = payload.get("content")
            if content:
                matches.append(f"[Past Conversation Summary]: {content}")

        return "\n".join(matches)
    except Exception as err:
        logger.warning("Error querying past conversation summary from Qdrant: %s", err)
        return ""
