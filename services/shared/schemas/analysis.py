from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# Structured critique and ATS audit output
class ResumeCritiqueOutput(BaseModel):
    overall_score: int = Field(default=85, ge=0, le=100, description="Overall resume quality score from 0 to 100")
    ats_compatibility_score: int = Field(default=85, ge=0, le=100, description="ATS parseability and keyword score")
    impact_metrics_score: int = Field(default=80, ge=0, le=100, description="Scoring based on quantifiable results and numbers")
    star_method_compliance: str = Field(default="Good alignment with Situation-Task-Action-Result format.", description="Assessment of Situation-Task-Action-Result format across bullets")
    key_strengths: List[str] = Field(default_factory=list, description="Top 3 to 5 distinct technical and professional strengths")
    critical_flaws: List[str] = Field(default_factory=list, description="High-priority weaknesses or missing elements")
    actionable_improvements: List[str] = Field(default_factory=list, description="Concrete line-by-line recommendations for improvement")


# Structured job description matching analysis output
class JDMatchOutput(BaseModel):
    match_percentage: int = Field(default=75, ge=0, le=100, description="Semantic fit percentage from 0 to 100")
    match_level: Literal["Strong Match", "Moderate Match", "Potential Match", "Low Match"] = Field(
        default="Moderate Match",
        description="Overall match tier"
    )
    matching_skills: List[str] = Field(default_factory=list, description="Skills in the resume that directly satisfy the JD")
    missing_critical_skills: List[str] = Field(default_factory=list, description="Required JD skills not found in the candidate resume")
    experience_alignment: str = Field(default="Experience demonstrates solid competency in required domain.", description="Evaluation of years of experience and domain relevancy")
    recommendations_to_pass: List[str] = Field(default_factory=list, description="Key adjustments needed to pass the initial screening")


class LearningMilestone(BaseModel):
    phase: str = Field(default="Phase 1: Foundation", description="Phase timeframe, e.g. 'Month 1-2: Foundations'")
    focus_skills: List[str] = Field(default_factory=list, description="Key technologies or methodologies to acquire")
    projects_to_build: List[str] = Field(default_factory=list, description="Practical portfolio projects demonstrating mastery")
    recommended_topics: List[str] = Field(default_factory=list, description="Specific concepts or system design patterns to study")


# Structured career growth and mock interview questions output
class CareerRoadmapOutput(BaseModel):
    current_level: str = Field(default="Mid-Level Professional", description="Assessed current level, e.g. Intern, Junior, Mid-Level, Senior")
    target_level: str = Field(default="Senior Engineer", description="Next target milestone, e.g. Senior AI Engineer")
    skill_gap_summary: str = Field(default="Needs advanced system design and production scale experience.", description="Summary of core technical competencies to bridge")
    learning_milestones: List[LearningMilestone] = Field(default_factory=list, description="Step-by-step progressive roadmap")
    mock_interview_questions: List[str] = Field(default_factory=list, description="3 to 5 high-yield technical interview questions")
