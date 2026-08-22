import os
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import google.generativeai as genai

from backend.database import get_db
from backend.routers.auth import get_current_user
from backend.models.models import User, Interview, Question, Answer, Report

router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        pass

class StartInterviewRequest(BaseModel):
    role: str = "Data Scientist"

class SubmitAnswerRequest(BaseModel):
    question_id: int
    interview_id: int
    answer_text: str

@router.post("/start")
@router.post("")
async def start_interview(
    payload: Optional[StartInterviewRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role = payload.role if payload else "Data Scientist"
    
    interview = Interview(
        user_id=current_user.id,
        role=role,
        status="in_progress",
        created_at=datetime.utcnow()
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    resume_context = current_user.resume_text or "Software Engineer with expertise in Python, SQL, and Machine Learning."
    
    # Generate Questions via Gemini or Fallback
    generated_questions = []
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"""
            You are an expert technical interviewer for a {role} role.
            Candidate resume context: {resume_context[:2000]}
            
            Generate exactly 5 distinct, high-impact technical and situational interview questions tailored to the resume.
            Return ONLY a JSON array of strings, for example:
            ["Can you describe a challenging project you built using Python?", "How do you optimize SQL query performance?"]
            """
            response = model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            generated_questions = json.loads(clean_text)
        except Exception as e:
            print("Gemini generation fallback:", e)

    if not generated_questions or not isinstance(generated_questions, list):
        generated_questions = [
            f"Can you walk me through the most technically challenging project on your resume and your specific architectural contributions?",
            f"How do you approach end-to-end data pipeline optimization and model deployment in production environments?",
            f"Describe an instance where your initial model or system design failed or underperformed. How did you debug and resolve it?",
            f"In a real-time system, how do you handle concurrency, latency bottlenecks, and database query optimization?",
            f"How do you evaluate trade-offs between model complexity, inference speed, and explainability when delivering features?"
        ]

    saved_questions = []
    for idx, q_text in enumerate(generated_questions, 1):
        q_obj = Question(
            interview_id=interview.id,
            question_text=str(q_text),
            order=idx
        )
        db.add(q_obj)
        saved_questions.append(q_obj)
    
    db.commit()

    return {
        "status": "success",
        "interview_id": interview.id,
        "total_questions": len(saved_questions),
        "current_question": {
            "id": saved_questions[0].id,
            "order": 1,
            "text": saved_questions[0].question_text
        },
        "questions": [{"id": q.id, "order": q.order, "text": q.question_text} for q in saved_questions]
    }

@router.get("/next-question/{interview_id}/{order}")
async def get_next_question(
    interview_id: int,
    order: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    question = db.query(Question).filter(
        Question.interview_id == interview_id,
        Question.order == order
    ).first()

    if not question:
        return {"completed": True}

    return {
        "completed": False,
        "question": {
            "id": question.id,
            "order": question.order,
            "text": question.question_text
        }
    }
