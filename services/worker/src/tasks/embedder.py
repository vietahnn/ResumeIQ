import logging
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client.models import PointStruct

from services.shared.config import settings
from services.shared.vector.qdrant_client import qdrant_service

logger = logging.getLogger("ResumeEmbedder")


class ResumeEmbedder:
    _model: Optional[Any] = None

    @classmethod
    def get_model(cls) -> Any:
        if cls._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model '{settings.EMBEDDING_MODEL}'...")
            cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return cls._model

    # Splits parsed resume components and raw text into semantically cohesive chunks
    @classmethod
    def chunk_resume(cls, parsed_data: Dict[str, Any], raw_text: str) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []

        summary = parsed_data.get("summary")
        skills = parsed_data.get("skills", [])
        contact = parsed_data.get("contact", {})

        profile_lines = []
        if contact.get("name"):
            profile_lines.append(f"Candidate: {contact['name']}")
        if contact.get("email"):
            profile_lines.append(f"Email: {contact['email']}")
        if contact.get("phone"):
            profile_lines.append(f"Phone: {contact['phone']}")
        if contact.get("github"):
            profile_lines.append(f"GitHub: {contact['github']}")
        if contact.get("linkedin"):
            profile_lines.append(f"LinkedIn: {contact['linkedin']}")
        if summary:
            profile_lines.append(f"Summary: {summary}")
        if skills:
            profile_lines.append(f"Key Technical Skills: {', '.join(skills)}")

        if profile_lines:
            chunks.append({
                "section": "profile_and_skills",
                "text": "\n".join(profile_lines),
                "metadata": {"skills": skills, "contact": contact}
            })

        experiences = parsed_data.get("experience") or parsed_data.get("sections", {}).get("experience", [])
        for exp in experiences:
            role = exp.get("role", "")
            company = exp.get("company", "")
            period = exp.get("period", "")
            bullets = exp.get("responsibilities") or exp.get("bullets", [])
            header = f"Role: {role} at {company} ({period})".strip()
            details = "\n".join(f"- {b}" for b in bullets) if bullets else ""
            content = f"{header}\n{details}".strip()
            if content:
                chunks.append({
                    "section": "experience",
                    "text": content,
                    "metadata": {"role": role, "company": company, "period": period}
                })

        projects = parsed_data.get("projects") or parsed_data.get("sections", {}).get("projects", [])
        for proj in projects:
            name = proj.get("name") or proj.get("title", "")
            tech = proj.get("technologies", "")
            bullets = proj.get("highlights") or proj.get("bullets", [])
            desc = proj.get("description", "")
            header = f"Project: {name}".strip()
            if tech:
                header += f" | Tech Stack: {tech}"
            body_parts = []
            if desc and desc not in bullets:
                body_parts.append(desc)
            if bullets:
                body_parts.extend(f"- {b}" for b in bullets)
            details = "\n".join(body_parts)
            content = f"{header}\n{details}".strip()
            if content:
                chunks.append({
                    "section": "projects",
                    "text": content,
                    "metadata": {"name": name, "technologies": tech}
                })

        education_items = parsed_data.get("education") or parsed_data.get("sections", {}).get("education", [])
        for edu in education_items:
            inst = edu.get("institution", "")
            deg = edu.get("degree", "")
            major = edu.get("major", "")
            period = edu.get("period", "")
            gpa = edu.get("gpa", "")
            content = f"Education: {deg or major}, {inst} ({period}) - GPA: {gpa}".strip()
            if content:
                chunks.append({
                    "section": "education",
                    "text": content,
                    "metadata": {"institution": inst, "degree": deg or major, "gpa": gpa}
                })

        if not chunks and raw_text:
            step = 600
            overlap = 100
            for i in range(0, len(raw_text), step - overlap):
                chunk_str = raw_text[i:i + step].strip()
                if chunk_str:
                    chunks.append({
                        "section": "raw_segment",
                        "text": chunk_str,
                        "metadata": {"offset": i}
                    })

        return chunks

    # Generates dense vectors for chunks and upserts points into Qdrant resumes collection
    @classmethod
    def embed_and_upsert(cls, resume_id: str, raw_text: str, parsed_data: Dict[str, Any]) -> int:
        qdrant_service.init_collections()
        chunks = cls.chunk_resume(parsed_data, raw_text)
        if not chunks:
            logger.warning(f"No chunks generated for resume_id='{resume_id}'")
            return 0

        model = cls.get_model()
        texts = [chunk["text"] for chunk in chunks]
        embeddings = model.encode(texts, normalize_embeddings=True)

        points: List[PointStruct] = []
        for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{resume_id}_{idx}"))
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector.tolist() if hasattr(vector, "tolist") else list(vector),
                    payload={
                        "resume_id": resume_id,
                        "chunk_index": idx,
                        "section": chunk["section"],
                        "content": chunk["text"],
                        "metadata": chunk.get("metadata", {})
                    }
                )
            )

        qdrant_service.upsert_vectors(
            collection_name=qdrant_service.COLLECTION_RESUMES,
            points=points
        )
        logger.info(f"Upserted {len(points)} vector chunks into Qdrant for resume_id='{resume_id}'")
        return len(points)
