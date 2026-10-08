from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResumeUploadedEvent(BaseEvent):
    resume_id: str
    file_name: str
    file_path: str
    user_id: Optional[str] = None


class ResumeProcessedEvent(BaseEvent):
    resume_id: str
    status: str
    skills_count: int = 0
    error_message: Optional[str] = None


class AnalysisRequestedEvent(BaseEvent):
    analysis_id: str
    resume_id: str
    target_jd: str
    job_title: Optional[str] = None


class NotificationEvent(BaseEvent):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    title: str
    message: str
    event_type: str = "INFO"
    payload: Optional[Dict[str, Any]] = None


class AgentTaskType(str, Enum):
    ATS_CRITIQUE = "ATS_CRITIQUE"
    JD_MATCHING = "JD_MATCHING"
    INTERVIEW_PREP = "INTERVIEW_PREP"
    JOB_SCOUT = "JOB_SCOUT"
    CONSOLIDATE_MEMORY = "CONSOLIDATE_MEMORY"


class AgentTaskRequestEvent(BaseEvent):
    task_id: str
    session_id: str
    user_id: Optional[str] = None
    resume_id: Optional[str] = None
    task_type: AgentTaskType
    payload: Dict[str, Any] = Field(default_factory=dict)


class AgentTaskResultEvent(BaseEvent):
    task_id: str
    session_id: str
    status: str  # "PROGRESS" | "SUCCESS" | "FAILED"
    task_type: AgentTaskType
    content: str
    metadata: Optional[Dict[str, Any]] = None
