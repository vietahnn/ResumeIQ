import logging
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import select

from services.shared.llm import llm_service
from services.shared.database.session import async_session_factory
from services.shared.database.models import Resume
from services.shared.schemas import ResumeCritiqueOutput

logger = logging.getLogger("CritiqueTask")

CRITIQUE_SYSTEM_PROMPT = (
    "You are an Elite Resume Critique and ATS Optimization Specialist. "
    "Audit the provided resume with high technical rigor:\n"
    "1. Score ATS Compatibility (0-100): Evaluate keyword density, formatting readability, and standard headings.\n"
    "2. Score Impact Metrics (0-100): Check if bullet points use quantifiable numbers, percentages, latency, or scale.\n"
    "3. Assess STAR Method: Analyze Situation, Task, Action, Result compliance.\n"
    "4. Highlight Key Strengths, Critical Flaws, and provide high-impact, actionable revisions for weak bullet points."
)


class CritiqueTask:
    # Analyzes resume structure, ATS readability, and STAR impact metrics
    @classmethod
    async def execute(cls, payload: Dict[str, Any], resume_id: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        resume_summary = ""
        if resume_id:
            try:
                async with async_session_factory() as db:
                    res_obj = (await db.execute(select(Resume).where(Resume.id == resume_id))).scalar_one_or_none()
                    if res_obj:
                        if res_obj.parsed_data:
                            pd = res_obj.parsed_data
                            parts = []
                            if pd.get("skills"):
                                parts.append(f"Skills: {', '.join(pd.get('skills', []))}")
                            for exp in pd.get("experience", []):
                                bullets = "\n".join(f"- {b}" for b in exp.get("responsibilities", []))
                                parts.append(f"Role: {exp.get('role')} at {exp.get('company')}\n{bullets}")
                            resume_summary = "\n\n".join(parts)
                        elif res_obj.raw_text:
                            resume_summary = res_obj.raw_text[:3500]
            except Exception as exc:
                logger.warning("DB read error in CritiqueTask: %s", exc)

        if not resume_summary:
            resume_summary = payload.get("user_query", "Sample candidate resume context")

        critique: ResumeCritiqueOutput = await llm_service.ainvoke_structured(
            prompt=f"Audit this candidate resume:\n\n{resume_summary}",
            schema=ResumeCritiqueOutput,
            system_prompt=CRITIQUE_SYSTEM_PROMPT
        )

        markdown_body = (
            f"### Đánh Giá CV & Chấm Điểm ATS (Tổng điểm: {critique.overall_score}/100)\n\n"
            f"- **Độ tương thích ATS:** {critique.ats_compatibility_score}/100\n"
            f"- **Chỉ số đo lường hiệu quả (Metrics):** {critique.impact_metrics_score}/100\n"
            f"- **Đánh giá chuẩn STAR:** {critique.star_method_compliance}\n\n"
            f"**Điểm mạnh nổi bật:**\n" + "\n".join(f"- {s}" for s in critique.key_strengths) + "\n\n"
            f"**Điểm yếu chí mạng:**\n" + "\n".join(f"- {f}" for f in critique.critical_flaws) + "\n\n"
            f"**Hành động cải thiện chi tiết:**\n" + "\n".join(f"- {a}" for a in critique.actionable_improvements)
        )

        return markdown_body, critique.model_dump()
