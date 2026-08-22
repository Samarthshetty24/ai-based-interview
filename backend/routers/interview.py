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
    role: Optional[str] = "Data Scientist"

class SubmitAnswerRequest(BaseModel):
    question_id: Optional[int] = None
    interview_id: Optional[int] = None
    answer_text: Optional[str] = ""

@router.post("/start")
@router.post("")
async def start_interview(
    payload: Optional[StartInterviewRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role = payload.role if payload and payload.role else "Data Scientist"
    
    interview = Interview(
        user_id=current_user.id,
        role=role,
        status="in_progress",
        created_at=datetime.utcnow()
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    resume_context = current_user.resume_text or "Data Scientist skilled in Python, Machine Learning, SQL, and FastAPI."
    
    generated_questions = []
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"""
            You are an expert technical interviewer for a {role} role.
            Candidate resume context: {resume_context[:2000]}
            
            Generate exactly 5 distinct, high-impact technical interview questions tailored to the candidate resume.
            Return ONLY a valid JSON array of 5 question strings, for example:
            ["Can you walk me through your recent project?", "How did you design the architecture?"]
            """
            response = model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            generated_questions = json.loads(clean_text)
        except Exception:
            pass

    if not generated_questions or not isinstance(generated_questions, list):
        generated_questions = [
            "Can you walk me through the most technically challenging project on your resume and your specific architectural contributions?",
            "How do you approach end-to-end data pipeline optimization and model deployment in production environments?",
            "Describe an instance where your initial system design failed or underperformed. How did you debug and resolve it?",
            "In a real-time system, how do you handle concurrency, latency bottlenecks, and query optimization?",
            "How do you evaluate trade-offs between model complexity, inference speed, and explainability when delivering features?"
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

    first_q = saved_questions[0]
    
    # Returns all standard key variations to prevent frontend undefined errors
    return {
        "status": "success",
        "interview_id": interview.id,
        "id": interview.id,
        "total_questions": len(saved_questions),
        "total": len(saved_questions),
        "question_index": 1,
        "order": 1,
        "question": first_q.question_text,
        "question_text": first_q.question_text,
        "text": first_q.question_text,
        "current_question": {
            "id": first_q.id,
            "order": 1,
            "index": 1,
            "text": first_q.question_text,
            "question": first_q.question_text,
            "question_text": first_q.question_text
        },
        "questions": [
            {
                "id": q.id,
                "order": q.order,
                "index": q.order,
                "text": q.question_text,
                "question": q.question_text,
                "question_text": q.question_text
            }
            for q in saved_questions
        ]
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
        return {"completed": True, "has_more": False}

    return {
        "completed": False,
        "has_more": True,
        "interview_id": interview_id,
        "order": question.order,
        "question_index": question.order,
        "question": question.question_text,
        "question_text": question.question_text,
        "text": question.question_text,
        "current_question": {
            "id": question.id,
            "order": question.order,
            "text": question.question_text,
            "question": question.question_text
        }
    }

@router.post("/submit-answer")
async def submit_answer(
    payload: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if payload.question_id:
        ans = Answer(
            question_id=payload.question_id,
            transcription=payload.answer_text or ""
        )
        db.add(ans)
        db.commit()

    return {"status": "success", "message": "Answer recorded"}
