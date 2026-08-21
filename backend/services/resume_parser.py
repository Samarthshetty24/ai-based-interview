import os

class ResumeParserService:
    @staticmethod
    def extract_text(file_path: str) -> str:
        text = ""
        try:
            import fitz
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text() + "\n"
            if text.strip():
                return text
        except Exception:
            pass

        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
            if text.strip():
                return text
        except Exception:
            pass

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            pass

        return text

    @classmethod
    def parse(cls, raw_text: str):
        from backend.services.ai_engine import DynamicZeroShotAIEngine
        return DynamicZeroShotAIEngine.extract_resume_entities(raw_text)
