import json
import re
from typing import List, Dict, Any
from backend.config import settings

class DynamicZeroShotAIEngine:
    @staticmethod
    def _call_gemini(prompt: str) -> str:
        if not getattr(settings, "GEMINI_API_KEY", None):
            return ""
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if res and res.text:
                return res.text
        except Exception:
            pass

        try:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=settings.GEMINI_API_KEY)
            model = genai_legacy.GenerativeModel("gemini-1.5-flash")
            res = model.generate_content(prompt)
            if res and res.text:
                return res.text
        except Exception:
            pass

        return ""

    @staticmethod
    def _clean_json(text: str) -> Dict[str, Any]:
        if not text:
            return {}
        cleaned = re.sub(r"^```json\s*", "", text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip("` \n\r\t")
        try:
            return json.loads(cleaned)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", cleaned)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    pass
        return {}

    @classmethod
    def detect_branch_and_entities(cls, raw_text: str) -> Dict[str, Any]:
        lower = (raw_text or "").lower()
        branch_scores = {
            "Computer Science": sum(1 for k in ["python", "sql", "machine learning", "data science", "fastapi", "react", "java", "dsa", "mongodb", "postgresql", "opencv", "mediapipe", "xgboost"] if k in lower),
            "ECE": sum(1 for k in ["vlsi", "embedded", "verilog", "microcontroller", "fpga", "signal processing", "rf"] if k in lower),
            "EEE": sum(1 for k in ["power systems", "matlab", "power electronics", "renewable energy", "electrical machines"] if k in lower),
            "Mechanical": sum(1 for k in ["solidworks", "cad", "ansys", "thermodynamics", "manufacturing", "autocad", "automotive"] if k in lower),
            "Civil": sum(1 for k in ["autocad", "staad pro", "revit", "structural", "geotechnical", "surveying"] if k in lower),
            "Architecture": sum(1 for k in ["bim", "rhino", "sketchup", "architectural design", "lumion", "urban planning"] if k in lower)
        }
        detected_branch = max(branch_scores, key=branch_scores.get)
        if branch_scores[detected_branch] == 0:
            detected_branch = "Computer Science"

        known_skills = [
            "Python", "SQL", "FastAPI", "PostgreSQL", "MongoDB", "Pandas", "Scikit-Learn",
            "XGBoost", "OpenCV", "MediaPipe", "Streamlit", "Docker", "Git", "Tableau",
            "Power BI", "R", "C++", "Java", "JavaScript", "React", "Machine Learning",
            "Deep Learning", "NLP", "Computer Vision", "Data Science", "Linux", "REST API"
        ]
        skills_found = [{"name": sk, "category": "Competency"} for sk in known_skills if re.search(r'\b' + re.escape(sk.lower()) + r'\b', lower)]

        lines = [l.strip() for l in raw_text.split("\n") if len(l.strip()) > 3]
        projects_found = []
        for idx, line in enumerate(lines):
            l_low = line.lower()
            if any(k in l_low for k in ["project", "experience", "system", "analyzer", "recommender"]) and len(line.split()) < 8:
                desc = lines[idx+1] if idx+1 < len(lines) else "Candidate technical project"
                if len(projects_found) < 3:
                    projects_found.append({"name": line[:60], "description": desc[:140]})

        if not projects_found:
            projects_found = [{"name": "AI Resume-Driven Analyzer", "description": "Candidate domain projects"}]

        return {
            "recommended_branch": detected_branch,
            "skills": skills_found if skills_found else [{"name": "Python", "category": "Language"}, {"name": "Data Science", "category": "Competency"}],
            "projects": projects_found
        }

    @classmethod
    def generate_question(cls, role: str, skills: List[str], projects: List[Dict], history: List[Dict], current_difficulty: str) -> Dict[str, str]:
        asked_questions = [h.get("question", "") for h in history]
        proj_names = [p.get("name", "") if isinstance(p, dict) else str(p) for p in projects]
        seq = len(history) + 1
        is_non_technical = (seq % 3 == 0)

        prompt = f"""
You are an expert interviewer conducting an interview for '{role}'.
CANDIDATE CONTEXT:
- Skills: {skills}
- Projects: {proj_names}
- Previous Questions: {json.dumps(asked_questions)}

Category: {'Behavioral & Situational' if is_non_technical else 'Technical Assessment'}

Output STRICT JSON only:
{{
  "question": "The question text",
  "topic": "{'Behavioral & Culture Fit' if is_non_technical else 'Technical Domain'}",
  "difficulty": "Medium",
  "type": "{'Behavioral & Situational' if is_non_technical else 'Technical Assessment'}"
}}
"""
        raw_resp = cls._call_gemini(prompt)
        parsed = cls._clean_json(raw_resp)
        if isinstance(parsed, dict) and parsed.get("question") and parsed.get("question") not in asked_questions:
            return {
                "question": str(parsed["question"]),
                "topic": str(parsed.get("topic", "Core Competency")),
                "difficulty": str(parsed.get("difficulty", current_difficulty or "Medium")),
                "type": str(parsed.get("type", "Technical Assessment"))
            }

        # Fallback question bank
        proj_sample = proj_names[0] if proj_names else "your key project"
        skill_sample = skills[0] if skills else "Python"

        if is_non_technical:
            fallbacks = [
                {"question": f"While building {proj_sample}, describe a time you faced technical roadblocks or tight deadlines. How did you prioritize?", "topic": "Ownership & Deadlines", "difficulty": "Medium", "type": "Behavioral & Situational"},
                {"question": f"How do you communicate technical decisions and trade-offs in {skill_sample} to non-technical team members?", "topic": "Communication & Collaboration", "difficulty": "Medium", "type": "Behavioral & Situational"},
                {"question": f"Tell me about a disagreement you had regarding architecture or priorities on {proj_sample} and how it was resolved.", "topic": "Conflict Resolution", "difficulty": "Medium", "type": "Behavioral & Situational"}
            ]
        else:
            fallbacks = [
                {"question": f"In your implementation of {proj_sample}, how did you design data preprocessing and prevent feature leakage using {skill_sample}?", "topic": "Architecture & Preprocessing", "difficulty": "Medium", "type": "Technical Assessment"},
                {"question": f"How did you evaluate overfitting versus underfitting and validate performance metrics for {proj_sample}?", "topic": "Model Validation", "difficulty": "Medium", "type": "Technical Assessment"},
                {"question": f"What bottlenecks did you encounter while scaling {skill_sample}, and what optimizations did you apply?", "topic": "Optimization & Scaling", "difficulty": "Hard", "type": "Technical Assessment"}
            ]

        for item in fallbacks:
            if item["question"] not in asked_questions:
                return item

        return fallbacks[0]

    @classmethod
    def evaluate_answer(cls, question: str, answer_transcript: str, duration: float) -> Dict[str, Any]:
        cleaned = (answer_transcript or "").strip()
        words = [w for w in cleaned.split() if len(w) > 1]
        if len(words) < 3:
            return {
                "overall_score": 0.0, "relevance_score": 0.0, "technical_score": 0.0,
                "completeness_score": 0.0, "communication_score": 0.0,
                "feedback": "No verbal or typed response detected."
            }

        prompt = f"""
Evaluate this answer:
Question: "{question}"
Candidate Answer: "{cleaned}"
Duration: {duration}s

Output STRICT JSON:
{{
  "overall_score": float (0-100),
  "relevance_score": float (0-100),
  "technical_score": float (0-100),
  "completeness_score": float (0-100),
  "communication_score": float (0-100),
  "feedback": "Actionable feedback"
}}
"""
        raw = cls._call_gemini(prompt)
        parsed = cls._clean_json(raw)
        if isinstance(parsed, dict) and parsed.get("overall_score") is not None:
            return parsed

        cnt = len(words)
        relevance = min(100.0, max(20.0, (cnt / 35.0) * 85.0))
        technical = min(100.0, relevance * 0.9)
        completeness = min(100.0, (cnt / 40.0) * 100.0)
        communication = 85.0 if cnt >= 15 else 50.0
        overall = round((relevance * 0.35) + (technical * 0.35) + (completeness * 0.15) + (communication * 0.15), 1)

        return {
            "overall_score": overall,
            "relevance_score": round(relevance, 1),
            "technical_score": round(technical, 1),
            "completeness_score": round(completeness, 1),
            "communication_score": round(communication, 1),
            "feedback": f"Evaluated {cnt} words for technical accuracy, structure, and communication."
        }
