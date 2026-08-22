import os
import json
from datetime import datetime
from typing import List, Optional, Any, Dict
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

class GenericRequest(BaseModel):
    role: Optional[str] = "Data Scientist"
    interview_id: Optional[int] = None
    question_id: Optional[int] = None
    order: Optional[int] = None
    question_index: Optional[int] = None
    answer_text: Optional[str] = ""
    answer: Optional[str] = ""

@router.post("/start")
@router.post("")
async def start_interview(
    payload: Optional[GenericRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role = (payload.role if payload and payload.role else "Data Scientist")
    
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
    
    questions_list = [
        "Can you walk me through the most technically challenging project on your resume and your specific architectural contributions?",
        "How do you approach end-to-end data pipeline optimization and model deployment in production environments?",
        "Describe an instance where your initial system design failed or underperformed. How did you debug and resolve it?",
        "In a real-time system, how do you handle concurrency, latency bottlenecks, and database query optimization?",
        "How do you evaluate trade-offs between model complexity, inference speed, and explainability when delivering features?"
    ]

    saved = []
    for idx, q_text in enumerate(questions_list, 1):
        q_obj = Question(
            interview_id=interview.id,
            question_text=q_text,
            order=idx
        )
        db.add(q_obj)
        saved.append(q_obj)
    db.commit()

    first_q = saved[0]
    return {
        "status": "success",
        "interview_id": interview.id,
        "id": interview.id,
        "total_questions": len(saved),
        "total": len(saved),
        "current_index": 1,
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
            {"id": q.id, "order": q.order, "index": q.order, "text": q.question_text, "question": q.question_text}
            for q in saved
        ]
    }

@router.post("/submit-answer")
@router.post("/next")
async def submit_and_get_next(
    payload: GenericRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    interview_id = payload.interview_id
    if not interview_id:
        last_int = db.query(Interview).filter(Interview.user_id == current_user.id).order_by(Interview.id.desc()).first()
        if last_int:
            interview_id = last_int.id

    if payload.question_id:
        ans_text = payload.answer_text or payload.answer or ""
        db.add(Answer(question_id=payload.question_id, transcription=ans_text))
        db.commit()

    current_idx = payload.order or payload.question_index or 1
    next_idx = current_idx + 1

    next_q = db.query(Question).filter(
        Question.interview_id == interview_id,
        Question.order == next_idx
    ).first()

    total_q = db.query(Question).filter(Question.interview_id == interview_id).count() or 5

    if not next_q or next_idx > total_q:
        if interview_id:
            int_obj = db.query(Interview).filter(Interview.id == interview_id).first()
            if int_obj:
                int_obj.status = "completed"
                db.commit()
        return {
            "status": "completed",
            "completed": True,
            "has_more": False,
            "interview_id": interview_id,
            "message": "Interview completed successfully"
        }

    return {
        "status": "success",
        "completed": False,
        "has_more": True,
        "interview_id": interview_id,
        "id": interview_id,
        "total_questions": total_q,
        "total": total_q,
        "current_index": next_idx,
        "question_index": next_idx,
        "order": next_idx,
        "question": next_q.question_text,
        "question_text": next_q.question_text,
        "text": next_q.question_text,
        "current_question": {
            "id": next_q.id,
            "order": next_idx,
            "index": next_idx,
            "text": next_q.question_text,
            "question": next_q.question_text,
            "question_text": next_q.question_text
        }
    }

@router.get("/next-question/{interview_id}/{order}")
async def get_next_question(
    interview_id: int,
    order: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    next_q = db.query(Question).filter(
        Question.interview_id == interview_id,
        Question.order == order
    ).first()

    total_q = db.query(Question).filter(Question.interview_id == interview_id).count() or 5

    if not next_q:
        return {"completed": True, "has_more": False, "total": total_q, "total_questions": total_q}

    return {
        "completed": False,
        "has_more": True,
        "interview_id": interview_id,
        "total_questions": total_q,
        "total": total_q,
        "current_index": order,
        "question_index": order,
        "order": order,
        "question": next_q.question_text,
        "question_text": next_q.question_text,
        "text": next_q.question_text,
        "current_question": {
            "id": next_q.id,
            "order": order,
            "index": order,
            "text": next_q.question_text,
            "question": next_q.question_text
        }
    }
