import uuid
import logging
from typing import Optional, Dict, Any, Tuple
from services.shared.config import settings
from services.shared.schemas.events import AgentTaskType, AgentTaskRequestEvent
from services.shared.kafka import shared_producer

logger = logging.getLogger("AgentTaskDispatcher")


class AgentTaskDispatcher:
    # Analyzes query keywords to determine whether it requires a heavy asynchronous worker task
    @staticmethod
    def detect_heavy_task(query: str, explicit_type: Optional[str] = None) -> Optional[AgentTaskType]:
        if explicit_type:
            try:
                return AgentTaskType(explicit_type)
            except ValueError:
                pass

        normalized = query.lower()
        if any(kw in normalized for kw in [
            "so khớp", "match jd", "độ phù hợp", "skill gap", "so sánh jd",
            "evaluate my resume fit", "resume fit", "job description", "semantic match",
            "fit against", "match with target jd", "jd semantic gap"
        ]):
            return AgentTaskType.JD_MATCHING
        if any(kw in normalized for kw in [
            "chấm điểm", "audit cv", "đánh giá cv", "ats score", "critique", "chuẩn ats",
            "review my cv", "review cv", "ats compatibility", "star bullet", "star method",
            "ats audit", "audit my bullet", "score my cv", "ats deep critique", "ats"
        ]):
            return AgentTaskType.ATS_CRITIQUE
        if any(kw in normalized for kw in [
            "phỏng vấn", "mock interview", "lộ trình học", "roadmap", "luyện phỏng vấn",
            "interview questions", "technical interview", "interview prep"
        ]):
            return AgentTaskType.INTERVIEW_PREP
        if any(kw in normalized for kw in [
            "tìm việc", "tìm job", "job search", "scout job", "tuyển dụng",
            "find jobs", "search jobs"
        ]):
            return AgentTaskType.JOB_SCOUT
        return None

    # Asynchronously packages and dispatches an analytical task to the Kafka worker queue
    async def dispatch_task(
        self,
        session_id: str,
        task_type: AgentTaskType,
        resume_id: Optional[str] = None,
        user_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> AgentTaskRequestEvent:
        task_id = str(uuid.uuid4())
        event = AgentTaskRequestEvent(
            task_id=task_id,
            session_id=session_id,
            user_id=user_id,
            resume_id=resume_id,
            task_type=task_type,
            payload=payload or {}
        )
        await shared_producer.send_event(settings.KAFKA_TOPIC_AGENT_TASKS, event)
        logger.info("Dispatched task %s (%s) to Kafka for session %s", task_id, task_type.value, session_id)
        return event


task_dispatcher = AgentTaskDispatcher()
