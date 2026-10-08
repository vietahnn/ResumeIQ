import io
import os
from pypdf import PdfReader
import docx


class DocumentParser:
    @staticmethod
    def extract_from_pdf(file_bytes: bytes) -> str:
        stream = io.BytesIO(file_bytes)
        reader = PdfReader(stream)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
        return "\n\n".join(text_parts)

    @staticmethod
    def extract_from_docx(file_bytes: bytes) -> str:
        stream = io.BytesIO(file_bytes)
        doc = docx.Document(stream)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    # Identifies file format and extracts normalized text content from binary document bytes
    @classmethod
    def parse(cls, file_bytes: bytes, file_name: str) -> str:
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()

        if ext == ".pdf":
            extracted = cls.extract_from_pdf(file_bytes)
        elif ext == ".docx":
            extracted = cls.extract_from_docx(file_bytes)
        else:
            raise ValueError(f"Unsupported document format: '{ext}'")

        if not extracted.strip():
            raise ValueError("Document appears to be empty or contains only non-extractable elements.")

        return extracted.strip()
