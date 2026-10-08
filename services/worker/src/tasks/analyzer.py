import logging
from typing import Dict, Any, Tuple, Optional, List
from sqlalchemy import select
from qdrant_client.models import Filter, FieldCondition, MatchValue

from services.shared.llm import llm_service
from services.shared.vector.qdrant_client import qdrant_service
from services.shared.database.session import async_session_factory
from services.shared.database.models import Resume, JobAnalysis
from services.shared.schemas import JDMatchOutput
from services.worker.src.tasks.embedder import ResumeEmbedder

logger = logging.getLogger("AnalyzerTask")

MATCHER_SYSTEM_PROMPT = (
    "You are an Advanced Technical Recruiter and Job Fit Analyst. "
    "Compare the candidate's resume context against the Job Description (JD):\n"
    "1. Calculate a calibrated match percentage (0-100) based on hard skills and project experience.\n"
    "2. Determine match level tier (Strong Match, Moderate Match, Potential Match, Low Match).\n"
    "3. Identify matching skills and missing critical skills.\n"
    "4. Assess experience alignment and provide clear recommendations to pass recruiter screening."
)


class AnalyzerTask:
    # Performs semantic vector retrieval and structured LLM evaluation to match CV with JD
    @classmethod
    async def execute(cls, payload: Dict[str, Any], resume_id: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        target_jd = payload.get("target_jd") or payload.get("user_query") or ""
        resume_context = ""
        retrieved_chunks: List[str] = []

        if resume_id:
            try:
                model = ResumeEmbedder.get_model()
                query_vector = model.encode(target_jd[:1000], normalize_embeddings=True).tolist()
                q_filter = Filter(must=[FieldCondition(key="resume_id", match=MatchValue(value=resume_id))])
                results = qdrant_service.search_vectors(
                    collection_name=qdrant_service.COLLECTION_RESUMES,
                    query_vector=query_vector,
                    limit=4,
                    query_filter=q_filter
                )
                for res in results:
                    data = getattr(res, "payload", {}) or {}
                    chunk = data.get("content")
                    if chunk:
                        retrieved_chunks.append(f"[{data.get('section', 'chunk')}]: {chunk}")
            except Exception as exc:
                logger.warning("Qdrant retrieval error in AnalyzerTask: %s", exc)

            try:
                async with async_session_factory() as db:
                    res_obj = (await db.execute(select(Resume).where(Resume.id == resume_id))).scalar_one_or_none()
                    if res_obj and res_obj.parsed_data:
                        pd = res_obj.parsed_data
                        resume_context = f"Skills: {pd.get('skills', [])}\nSummary: {pd.get('summary', '')}"
            except Exception as exc:
                logger.warning("DB read error in AnalyzerTask: %s", exc)

        combined_resume = "\n".join(retrieved_chunks) or resume_context or "General Software Engineer Candidate"
        prompt = f"Candidate Resume:\n{combined_resume}\n\nTarget Job Description:\n{target_jd}"

        match_output: JDMatchOutput = await llm_service.ainvoke_structured(
            prompt=prompt,
            schema=JDMatchOutput,
            system_prompt=MATCHER_SYSTEM_PROMPT
        )

        # Persists analysis records into PostgreSQL job_analyses
        if resume_id:
            try:
                async with async_session_factory() as db:
                    record = JobAnalysis(
                        resume_id=resume_id,
                        target_jd=target_jd[:1500],
                        ats_score=float(match_output.match_percentage),
                        match_details=match_output.model_dump(),
                        skill_gap={"missing_critical_skills": match_output.missing_critical_skills}
                    )
                    db.add(record)
                    await db.commit()
            except Exception as exc:
                logger.error("Failed saving JobAnalysis record: %s", exc)

        markdown_body = (
            f"### Kết Quả So Khớp CV với JD (Match Score: {match_output.match_percentage}% - {match_output.match_level})\n\n"
            f"**Kỹ năng đáp ứng:** {', '.join(match_output.matching_skills)}\n\n"
            f"**Kỹ năng còn thiếu (Skill Gaps):** {', '.join(match_output.missing_critical_skills)}\n\n"
            f"**Đánh giá kinh nghiệm:** {match_output.experience_alignment}\n\n"
            f"**Khuyến nghị cải thiện:**\n" + "\n".join(f"- {r}" for r in match_output.recommendations_to_pass)
        )

        return markdown_body, match_output.model_dump()
