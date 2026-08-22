import os
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.routers.auth import get_current_user
from backend.models.models import User, Interview, Question, Answer

router = APIRouter()
IGNORED = {"", "undefined", "null", "none", "answer submitted", "candidate submitted response."}

@router.get("/summary/{interview_id}")
@router.get("/{interview_id}")
async def get_interview_report(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        interview = db.query(Interview).filter(Interview.user_id == current_user.id).order_by(Interview.id.desc()).first()
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

    questions = db.query(Question).filter(Question.interview_id == interview.id).all()
    q_ids = [q.id for q in questions]
    answers = db.query(Answer).filter(Answer.question_id.in_(q_ids)).all() if q_ids else []

    role = interview.role or "Data Scientist"
    date_str = interview.created_at.strftime("%b %d, %Y") if interview.created_at else datetime.utcnow().strftime("%b %d, %Y")

    valid_words = 0
    valid_count = 0
    keywords = []

    for q in questions:
        ans = next((a for a in answers if a.question_id == q.id), None)
        txt = (ans.transcription if ans else "").strip().lower()
        if txt not in IGNORED and len(txt.split()) >= 3:
            valid_count += 1
            valid_words += len(txt.split())
            kw = re.findall(r"\b(python|sql|machine learning|deep learning|data|model|pipeline|api|docker|tableau)\b", txt)
            keywords.extend(kw)

    # If the candidate skipped or gave empty answers
    if valid_count == 0 or valid_words < 6:
        return {
            "status": "success",
            "candidate_name": current_user.email.split("@")[0].upper(),
            "role": role,
            "date": date_str,
            "overall_score": 0.0,
            "radar": {
                "Technical Depth": 0,
                "System Architecture": 0,
                "Communication Clarity": 0,
                "Problem Solving": 0,
                "Tool Proficiency": 0
            },
            "strengths": ["No verbal or written answers recorded."],
            "weaknesses": ["Candidate did not respond to technical questions."],
            "recommendations": ["Enable microphone and speak clearly, or type responses actively."]
        }

    # Deterministic scoring based on actual input
    depth = min(95, valid_words * 2 + len(set(keywords)) * 8)
    arch = min(90, int(depth * 0.85))
    comm = min(95, int((valid_count / 5.0) * 90))
    prob = min(90, int(depth * 0.88))
    tools = min(95, len(set(keywords)) * 22)

    overall = round((depth + arch + comm + prob + tools) / 50.0, 1)

    return {
        "status": "success",
        "candidate_name": current_user.email.split("@")[0].upper(),
        "role": role,
        "date": date_str,
        "overall_score": overall,
        "radar": {
            "Technical Depth": int(depth),
            "System Architecture": int(arch),
            "Communication Clarity": int(comm),
            "Problem Solving": int(prob),
            "Tool Proficiency": int(tools)
        },
        "strengths": [
            f"Candidate answered {valid_count} of 5 questions with domain context.",
            f"Demonstrated awareness of: {', '.join(set(keywords)) if keywords else 'Core engineering concepts'}."
        ],
        "weaknesses": [
            f"Skipped or gave very short explanations on {5 - valid_count} questions.",
            "Can provide deeper discussion on production scaling and trade-offs."
        ],
        "recommendations": [
            "Use STAR methodology for structured answers.",
            "Provide quantitative metrics when describing past project impacts."
        ]
    }
