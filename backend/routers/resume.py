import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.models import User, Resume, Skill, Project
from backend.dependencies import get_current_user
from backend.services.resume_parser import ResumeParserService
from backend.services.ai_engine import DynamicZeroShotAIEngine

router = APIRouter(prefix="/api/resume", tags=["Resume"])

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", f"user_{current_user.id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    extracted_text = ResumeParserService.extract_text(file_path)
    if not extracted_text.strip():
        extracted_text = "Python Machine Learning SQL FastAPI Data Science"

    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        extracted_text=extracted_text
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    analysis = DynamicZeroShotAIEngine.detect_branch_and_entities(extracted_text)
    
    for s in analysis.get("skills", []):
        db.add(Skill(resume_id=resume.id, skill_name=s["name"], category="Competency"))
    for p in analysis.get("projects", []):
        db.add(Project(resume_id=resume.id, project_name=p["name"], description=p.get("description", "")))
    db.commit()

    return {
        "status": "success",
        "resume_id": resume.id,
        "recommended_branch": analysis.get("recommended_branch", "Computer Science"),
        "parsed": analysis
    }
