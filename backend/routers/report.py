from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.models import User, Interview
from backend.dependencies import get_current_user

router = APIRouter(prefix="/api/report", tags=["Report"])

@router.get("/{interview_id}")
def get_report(interview_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == current_user.id).first()
    if not interview or not interview.report:
        raise HTTPException(status_code=404, detail="Report not generated")

    return {
        "candidate_name": current_user.name,
        "role": interview.role,
        "date": interview.started_at.strftime("%B %d, %Y"),
        "overall_score": interview.report.overall_score,
        "technical_score": interview.report.technical_score,
        "communication_score": interview.report.communication_score,
        "speech_score": interview.report.speech_score,
        "presentation_score": interview.report.presentation_score,
        "strengths": interview.report.strengths,
        "weaknesses": interview.report.weaknesses,
        "recommendations": interview.report.recommendations
    }

@router.get("/history/all")
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interviews = db.query(Interview).filter(Interview.user_id == current_user.id, Interview.status == "completed").order_by(Interview.started_at.desc()).all()
    return [{"id": i.id, "role": i.role, "score": i.overall_score, "date": i.started_at.strftime("%Y-%m-%d")} for i in interviews]
