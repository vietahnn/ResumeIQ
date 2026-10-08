import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.config import settings
from services.shared.database import get_db, Resume, ResumeStatus
from services.shared.storage import minio_storage
from services.shared.schemas import ResumeUploadedEvent
from services.shared.kafka import shared_producer as kafka_producer
from services.shared.redis import check_rate_limit

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


class ResumeUploadResponse(BaseModel):
    resume_id: str
    file_name: str
    file_path: str
    status: str
    message: str


class ResumeDetailResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    file_name: str
    file_path: str
    status: str
    raw_text: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Validates uploaded resume, stores in MinIO, creates database record, and publishes Kafka event
@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a resume file"
)
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> ResumeUploadResponse:
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, remaining, retry_after = await check_rate_limit(
        key=f"ratelimit:upload:{client_ip}",
        limit=3,
        window_seconds=60
    )
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many upload requests. Maximum 3 uploads per minute allowed. Please try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)}
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only .pdf and .docx are allowed."
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    resume_id = str(uuid.uuid4())
    object_name = f"resumes/{resume_id}_{file.filename}"

    try:
        minio_storage.upload_bytes(
            object_name=object_name,
            data=file_bytes,
            content_type=file.content_type or "application/octet-stream"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store resume in object storage: {exc}"
        )

    resume_record = Resume(
        id=resume_id,
        user_id=user_id,
        file_name=file.filename,
        file_path=object_name,
        status=ResumeStatus.PENDING
    )
    db.add(resume_record)
    await db.commit()
    await db.refresh(resume_record)

    event = ResumeUploadedEvent(
        resume_id=resume_id,
        file_name=file.filename,
        file_path=object_name,
        user_id=user_id
    )
    await kafka_producer.send_event(
        topic=settings.KAFKA_TOPIC_RESUME_UPLOADED,
        event_data=event
    )

    return ResumeUploadResponse(
        resume_id=resume_id,
        file_name=file.filename,
        file_path=object_name,
        status=ResumeStatus.PENDING.value,
        message="Resume uploaded successfully and queued for background analysis."
    )


# Retrieves details, status, and parsed profile data for a specific resume
@router.get(
    "/{resume_id}",
    response_model=ResumeDetailResponse,
    summary="Get resume details and processing status"
)
async def get_resume_status(
    resume_id: str,
    db: AsyncSession = Depends(get_db)
) -> ResumeDetailResponse:
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with id '{resume_id}' not found."
        )

    return ResumeDetailResponse(
        id=resume.id,
        user_id=resume.user_id,
        file_name=resume.file_name,
        file_path=resume.file_path,
        status=resume.status.value,
        raw_text=resume.raw_text,
        parsed_data=resume.parsed_data,
        error_message=resume.error_message,
        created_at=resume.created_at,
        updated_at=resume.updated_at
    )


# Lists uploaded resumes with pagination support
@router.get(
    "/",
    response_model=List[ResumeDetailResponse],
    summary="List all uploaded resumes"
)
async def list_resumes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> List[ResumeDetailResponse]:
    query = select(Resume).order_by(Resume.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    resumes = result.scalars().all()

    return [
        ResumeDetailResponse(
            id=r.id,
            user_id=r.user_id,
            file_name=r.file_name,
            file_path=r.file_path,
            status=r.status.value,
            raw_text=r.raw_text,
            parsed_data=r.parsed_data,
            error_message=r.error_message,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in resumes
    ]
