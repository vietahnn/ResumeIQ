import logging
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import select

from services.shared.llm import llm_service
from services.shared.database.session import async_session_factory
from services.shared.database.models import Resume
from services.shared.schemas import CareerRoadmapOutput

logger = logging.getLogger("CoachTask")

COACH_SYSTEM_PROMPT = (
    "You are an Executive Tech Career Coach and Senior Staff Technical Interviewer. "
    "Given candidate profile context and target role, generate a comprehensive career acceleration plan and mock interview questions:\n"
    "1. Gauge current seniority tier accurately and output as `current_level` (e.g., 'Junior AI Engineer', 'Mid-Level Backend', 'Senior Platform Engineer').\n"
    "2. Determine the next tier as `target_level` (e.g., 'Senior AI Engineer', 'Staff Platform Lead').\n"
    "3. Synthesize critical competency gaps in `skill_gap_summary`.\n"
    "4. Build milestone-based learning plans in `learning_milestones`.\n"
    "5. Formulate 3-5 real-world situational and technical interview questions testing edge cases in `mock_interview_questions`.\n"
    "Ensure all schema fields are provided."
)


class CoachTask:
    # Generates a progressive learning roadmap and situational mock interview questions
    @classmethod
    async def execute(cls, payload: Dict[str, Any], resume_id: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        target_role = payload.get("target_role") or "Senior Software Engineer"
        user_query = payload.get("user_query") or ""
        resume_context = ""

        if resume_id:
            try:
                async with async_session_factory() as db:
                    res_obj = (await db.execute(select(Resume).where(Resume.id == resume_id))).scalar_one_or_none()
                    if res_obj:
                        pd = res_obj.parsed_data or {}
                        resume_context = f"Skills: {pd.get('skills', [])}\nSummary: {pd.get('summary', '')}"
            except Exception as exc:
                logger.warning("DB read error in CoachTask: %s", exc)

        prompt = (
            f"Target Role: {target_role}\n"
            f"User Goal: {user_query}\n"
            f"Candidate Context: {resume_context or 'Software Developer'}"
        )

        roadmap: CareerRoadmapOutput = await llm_service.ainvoke_structured(
            prompt=prompt,
            schema=CareerRoadmapOutput,
            system_prompt=COACH_SYSTEM_PROMPT
        )

        milestones_text = []
        for m in roadmap.learning_milestones:
            milestones_text.append(
                f"#### {m.phase}\n"
                f"- **Kỹ năng trọng tâm:** {', '.join(m.focus_skills) if m.focus_skills else 'Kiến thức cốt lõi'}\n"
                f"- **Dự án thực chiến:** {', '.join(m.projects_to_build) if m.projects_to_build else 'Xây dựng dịch vụ phân tán'}\n"
                f"- **Chủ đề nghiên cứu:** {', '.join(m.recommended_topics) if m.recommended_topics else 'Thiết kế hệ thống và tối ưu hiệu năng'}"
            )

        if not milestones_text:
            milestones_text.append("- Tiếp tục nâng cao kiến thức nền tảng, thiết kế hệ thống và giải quyết bài toán quy mô lớn.")

        if roadmap.mock_interview_questions:
            questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(roadmap.mock_interview_questions))
        else:
            questions_text = (
                "1. Bạn xử lý bài toán dữ liệu lớn và độ trễ thấp như thế nào trong hệ thống của mình?\n"
                "2. Khi hệ thống gặp nghẽn cổ chai (bottleneck) ở cơ sở dữ liệu, bạn áp dụng chiến lược caching nào?\n"
                "3. Chia sẻ một sự cố kỹ thuật nghiêm trọng bạn từng giải quyết và bài học rút ra."
            )

        markdown_body = (
            f"### Lộ Trình Phát Triển Sự Nghiệp & Luyện Phỏng Vấn\n\n"
            f"**Cấp độ hiện tại:** {roadmap.current_level} ➔ **Mục tiêu:** {roadmap.target_level}\n\n"
            f"**Tóm tắt khoảng cách năng lực (Skill Gap):** {roadmap.skill_gap_summary}\n\n"
            f"### Lộ Trình Học Tập Từng Giai Đoạn:\n" + "\n\n".join(milestones_text) + "\n\n"
            f"### Bộ Câu Hỏi Phỏng Vấn Tình Huống Thực Chiến (Mock Interview):\n{questions_text}"
        )

        return markdown_body, roadmap.model_dump()
