import os
import json
import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import google.generativeai as genai

from backend.database import get_db
from backend.routers.auth import get_current_user
from backend.models.models import User, Resume, Interview, Question, Answer

load_dotenv()
router = APIRouter()

class GenericRequest(BaseModel):
    role: Optional[str] = "Data Scientist"
    interview_id: Optional[int] = None
    question_id: Optional[int] = None
    order: Optional[int] = None
    question_index: Optional[int] = None
    answer_text: Optional[str] = ""
    answer: Optional[str] = ""

@router.post("")
@router.post("/start")
async def start_interview(
    payload: Optional[GenericRequest] = None,
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

    resume_text = (current_user.resume_text or "").strip()
    if not resume_text:
        latest_res = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.id.desc()).first()
        if latest_res and latest_res.raw_text:
            resume_text = latest_res.raw_text.strip()

    questions_data = [
        f"Can you explain your experience and architectural approach when implementing machine learning pipelines for a {role} project?",
        "What strategies do you use for hyperparameter tuning, model evaluation, and preventing overfitting on complex datasets?",
        "How do you approach database schema design, indexing, and optimizing expensive queries in production systems?",
        "What challenges have you encountered with data preprocessing, cleaning, and handling missing values in large datasets?",
        "When balancing computational latency against model complexity in production deployments, what trade-offs do you evaluate?"
    ]

    saved_questions = []
    for idx, q_text in enumerate(questions_data, 1):
        q = Question(interview_id=interview.id, question_text=q_text, order=idx)
        db.add(q)
        saved_questions.append(q)
    db.commit()

    first_q = saved_questions[0]
    return {
        "status": "success",
        "interview_id": interview.id,
        "id": interview.id,
        "total_questions": len(saved_questions),
        "total": len(saved_questions),
        "current_index": 1,
        "question_index": 1,
        "order": 1,
        "question": first_q.question_text,
        "question_text": first_q.question_text,
        "text": first_q.question_text,
        "questions": [{"id": q.id, "order": q.order, "text": q.question_text} for q in saved_questions]
    }

@router.post("/submit-answer")
@router.post("/next")
async def submit_answer(
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
        ans = payload.answer_text or payload.answer or ""
        db.add(Answer(question_id=payload.question_id, transcription=ans))
        db.commit()

    current_idx = payload.order or payload.question_index or 1
    next_idx = current_idx + 1

    total_q = db.query(Question).filter(Question.interview_id == interview_id).count() or 5
    next_q = db.query(Question).filter(
        Question.interview_id == interview_id,
        Question.order == next_idx
    ).first()

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
            "interview_id": interview_id
        }

    return {
        "status": "success",
        "completed": False,
        "has_more": True,
        "interview_id": interview_id,
        "total_questions": total_q,
        "total": total_q,
        "current_index": next_idx,
        "question_index": next_idx,
        "order": next_idx,
        "question": next_q.question_text,
        "question_text": next_q.question_text,
        "text": next_q.question_text
    }
