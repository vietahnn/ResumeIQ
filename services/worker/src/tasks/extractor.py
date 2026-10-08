import re
from typing import Dict, Any, List, Set, Optional


class ProfileExtractor:
    TECH_SKILLS_TAXONOMY: Set[str] = {
        # Programming Languages
        "python", "java", "c++", "c#", "c", "javascript", "typescript", "golang", "go",
        "rust", "php", "ruby", "kotlin", "swift", "r", "scala", "dart", "sql", "html", "css",

        # AI / Machine Learning / Data Science
        "machine learning", "deep learning", "nlp", "natural language processing",
        "computer vision", "llm", "large language models", "rag", "langchain", "langgraph",
        "pytorch", "tensorflow", "keras", "scikit-learn", "opencv", "huggingface",
        "transformers", "pandas", "numpy", "matplotlib", "seaborn", "scipy", "spark",
        "hadoop", "mlops", "data analysis", "data engineering", "embeddings",
        "litellm", "bert", "gpt", "clip", "yolo", "webrtc", "onnx", "whisper",

        # Web & Backend Frameworks
        "fastapi", "django", "flask", "express", "express.js", "nestjs", "spring boot",
        "react", "react.js", "next.js", "vue", "vue.js", "angular", "node.js", "nodejs",
        "graphql", "rest api", "grpc", "tailwind", "tailwind css", "bootstrap", "sqlalchemy",

        # Databases & Storage
        "postgresql", "postgres", "mysql", "mongodb", "redis", "qdrant", "chromadb",
        "pinecone", "elasticsearch", "sqlite", "cassandra", "minio", "dynamodb", "supabase",

        # DevOps, Cloud & Tools
        "docker", "docker compose", "kubernetes", "k8s", "aws", "gcp", "google cloud",
        "azure", "kafka", "apache kafka", "rabbitmq", "git", "github", "gitlab",
        "ci/cd", "github actions", "jenkins", "terraform", "ansible", "nginx", "linux"
    }

    PREPOSITIONS: Set[str] = {
        "through", "with", "and", "or", "to", "by", "via", "for", "in", "on", "at",
        "of", "the", "a", "an", "into", "using", "from", "over", "under"
    }

    # Extracts structured profile components, contact details, skills, experience, and projects
    @classmethod
    def extract(cls, raw_text: str) -> Dict[str, Any]:
        if not raw_text:
            return {"contact": {}, "skills": [], "experience": [], "projects": [], "education": []}

        contact = cls._extract_contact_info(raw_text)
        skills = cls._extract_skills(raw_text)
        sections = cls._split_sections(raw_text)

        experience = cls._extract_experience(sections.get("Experience", ""))
        projects = cls._extract_projects(sections.get("Projects", ""))
        education = cls._extract_education(sections.get("Education", ""))

        return {
            "contact": contact,
            "skills": skills,
            "skills_count": len(skills),
            "experience": experience,
            "projects": projects,
            "education": education
        }

    @staticmethod
    def _extract_contact_info(text: str) -> Dict[str, Any]:
        contact: Dict[str, Any] = {
            "email": None,
            "phone": None,
            "github": None,
            "linkedin": None,
            "links": []
        }

        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if email_match:
            contact["email"] = email_match.group(0).lower()

        phone_match = re.search(r"(?:\+?84|0)(?:[\s\.-]?\d){9,10}", text)
        if phone_match:
            contact["phone"] = phone_match.group(0).strip()

        github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([\w\.-]+)", text, re.IGNORECASE)
        if github_match:
            contact["github"] = f"https://github.com/{github_match.group(1)}"

        linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([\w\.-]+)", text, re.IGNORECASE)
        if linkedin_match:
            contact["linkedin"] = f"https://linkedin.com/in/{linkedin_match.group(1)}"

        generic_links = re.findall(r"https?://[^\s\|]+", text)
        contact["links"] = [l for l in set(generic_links) if "github.com" not in l and "linkedin.com" not in l]

        return contact

    @classmethod
    def _extract_skills(cls, text: str) -> List[str]:
        cleaned_text = re.sub(r"[^\w\s\+\#\./-]", " ", text.lower())
        tokens = set(re.split(r"[\s,;/\n\(\)]+", cleaned_text))
        matched_skills: Set[str] = set()

        for skill in cls.TECH_SKILLS_TAXONOMY:
            if " " in skill:
                if skill in text.lower():
                    matched_skills.add(skill.title())
            else:
                if skill in tokens:
                    matched_skills.add(skill.upper() if len(skill) <= 3 else skill.title())

        return sorted(list(matched_skills))

    @staticmethod
    def _split_sections(text: str) -> Dict[str, str]:
        pattern = r"^(About Me|Technical Skills|Experience|Kinh nghiệm|Projects|Dự án|Education|Học vấn|Publications)\s*$"
        parts = re.split(pattern, text, flags=re.MULTILINE)

        sections: Dict[str, str] = {}
        for i in range(1, len(parts), 2):
            sec_name = parts[i].strip()
            sec_content = parts[i+1].strip()
            if "experience" in sec_name.lower() or "kinh nghiệm" in sec_name.lower():
                sections["Experience"] = sec_content
            elif "project" in sec_name.lower() or "dự án" in sec_name.lower():
                sections["Projects"] = sec_content
            elif "education" in sec_name.lower() or "học vấn" in sec_name.lower():
                sections["Education"] = sec_content
            else:
                sections[sec_name] = sec_content

        return sections

    @staticmethod
    def _extract_experience(exp_text: str) -> List[Dict[str, Any]]:
        if not exp_text:
            return []

        lines = [l.strip() for l in exp_text.splitlines() if l.strip()]
        date_pattern = r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}|\d{4})\s*[–\-]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}|\d{4}|Present|Hiện tại)"

        experiences: List[Dict[str, Any]] = []
        current_exp: Optional[Dict[str, Any]] = None

        for line in lines:
            date_match = re.search(date_pattern, line, re.IGNORECASE)
            if date_match and not line.startswith("•") and not line.startswith("-"):
                if current_exp:
                    experiences.append(current_exp)

                period = date_match.group(0).strip()
                role_raw = line[:date_match.start()].strip()
                current_exp = {
                    "role": role_raw or "Software / AI Engineer",
                    "company": "",
                    "period": period,
                    "responsibilities": []
                }
            elif current_exp:
                if line.startswith("•") or line.startswith("-"):
                    current_exp["responsibilities"].append(line.lstrip("•- ").strip())
                elif current_exp["responsibilities"]:
                    current_exp["responsibilities"][-1] += " " + line
                elif not current_exp["company"]:
                    current_exp["company"] = line

        if current_exp:
            experiences.append(current_exp)

        return experiences

    @classmethod
    def _is_project_title(cls, line: str, prev_line: str) -> bool:
        if line.startswith("•") or line.startswith("-"):
            return False
        if len(line) > 70 or len(line) < 4:
            return False
        if line.endswith((".", ",", ";", ":")):
            return False

        prev_words = prev_line.strip().split()
        if prev_words and prev_words[-1].lower() in cls.PREPOSITIONS:
            return False

        lower = line.lower()
        if lower.startswith(("and", "or", "to", "with", "via", "for", "in", "by", "at", "from", "into", "of", "quality", "search")):
            return False
        if not line[0].isupper():
            return False

        keywords = ["system", "platform", "app", "chatbot", "bot", "assistant", "pipeline", "tool", "model", "meetbridge", "mygpt"]
        if any(k in lower for k in keywords):
            return True

        words = [w for w in line.split() if w.isalpha()]
        if words and sum(1 for w in words if w[0].isupper()) / len(words) >= 0.6:
            return True
        return False

    @classmethod
    def _extract_projects(cls, proj_text: str) -> List[Dict[str, Any]]:
        if not proj_text:
            return []

        lines = [l.strip() for l in proj_text.splitlines() if l.strip()]
        projects: List[Dict[str, Any]] = []
        curr_proj: Optional[Dict[str, Any]] = None

        for i, line in enumerate(lines):
            prev_line = lines[i-1] if i > 0 else ""
            if line.startswith("•") or line.startswith("-"):
                if curr_proj:
                    curr_proj["highlights"].append(line.lstrip("•- ").strip())
            elif cls._is_project_title(line, prev_line):
                if curr_proj:
                    projects.append(curr_proj)
                curr_proj = {"name": line, "highlights": [], "description": ""}
            elif curr_proj and curr_proj["highlights"]:
                curr_proj["highlights"][-1] += " " + line

        if curr_proj:
            projects.append(curr_proj)

        for p in projects:
            p["description"] = p["highlights"][0] if p["highlights"] else ""

        return projects

    @staticmethod
    def _extract_education(edu_text: str) -> List[Dict[str, Any]]:
        if not edu_text:
            return []

        lines = [l.strip() for l in edu_text.splitlines() if l.strip()]
        inst_line = lines[0] if lines else ""

        date_match = re.search(r"(?:Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul)[a-z]*\.?\s*\d{4}.*", inst_line)
        period = date_match.group(0).strip() if date_match else ""
        inst = inst_line.replace(period, "").strip() if date_match else inst_line

        major = ""
        gpa = ""
        for line in lines[1:]:
            m_match = re.search(r"Major:\s*([^|\n]+)", line)
            if m_match:
                major = m_match.group(1).strip()
            g_match = re.search(r"GPA:\s*([\d\./]+)", line)
            if g_match:
                gpa = g_match.group(1).strip()

        return [{
            "institution": inst,
            "degree": major,
            "period": period,
            "gpa": gpa
        }]
