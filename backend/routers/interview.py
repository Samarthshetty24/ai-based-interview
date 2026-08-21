import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.models import User, Resume, Interview, Question, Answer, Report
from backend.schemas.schemas import InterviewCreate, AnswerSubmit
from backend.dependencies import get_current_user
from backend.services.ai_engine import DynamicZeroShotAIEngine

router = APIRouter(prefix="/api/interview", tags=["Interview"])

@router.post("/start")
def start_interview(payload: InterviewCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.uploaded_at.desc()).first()
    
    interview = Interview(
        user_id=current_user.id,
        resume_id=resume.id if resume else None,
        role=payload.role,
        difficulty=payload.difficulty or "Medium",
        total_questions=payload.total_questions or 5
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    skills = [s.skill_name for s in resume.skills] if (resume and resume.skills) else []
    projects = [{"name": p.project_name, "description": p.description} for p in resume.projects] if (resume and resume.projects) else []

    dynamic_q = DynamicZeroShotAIEngine.generate_question(
        role=payload.role,
        skills=skills,
        projects=projects,
        history=[],
        current_difficulty=payload.difficulty or "Medium"
    )

    q_text = dynamic_q.get("question") or f"Describe your practical experience and system architecture when working with {payload.role}."
    q_topic = dynamic_q.get("topic") or "Technical Assessment"
    q_diff = dynamic_q.get("difficulty") or (payload.difficulty or "Medium")
    q_type = dynamic_q.get("type") or "Resume-Grounded"

    question = Question(
        interview_id=interview.id,
        question_text=q_text,
        question_type=q_type,
        topic=q_topic,
        difficulty=q_diff,
        sequence_number=1
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return {
        "interview_id": interview.id,
        "question_id": question.id,
        "sequence_number": 1,
        "total_questions": interview.total_questions,
        "question_text": question.question_text,
        "topic": question.topic,
        "difficulty": question.difficulty
    }

@router.post("/submit-answer")
def submit_answer(payload: AnswerSubmit, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(Interview.id == payload.interview_id, Interview.user_id == current_user.id).first()
    question = db.query(Question).filter(Question.id == payload.question_id, Question.interview_id == payload.interview_id).first()
    if not interview or not question:
        raise HTTPException(status_code=404, detail="Session not found")

    eval_result = DynamicZeroShotAIEngine.evaluate_answer(
        question=question.question_text,
        answer_transcript=payload.transcript,
        duration=payload.duration
    )

    answer = Answer(
        question_id=question.id,
        transcript=payload.transcript,
        duration=payload.duration,
        overall_score=eval_result.get("overall_score", 0.0),
        relevance_score=eval_result.get("relevance_score", 0.0),
        technical_score=eval_result.get("technical_score", 0.0),
        completeness_score=eval_result.get("completeness_score", 0.0),
        communication_score=eval_result.get("communication_score", 0.0),
        feedback=eval_result.get("feedback", "")
    )
    db.add(answer)
    db.commit()

    if question.sequence_number >= interview.total_questions:
        interview.status = "completed"
        interview.completed_at = datetime.datetime.utcnow()
        all_answers = db.query(Answer).join(Question).filter(Question.interview_id == interview.id).all()
        
        avg_score = round(sum(a.overall_score for a in all_answers) / max(1, len(all_answers)), 1)
        tech_score = round(sum(a.technical_score for a in all_answers) / max(1, len(all_answers)), 1)
        comm_score = round(sum(a.communication_score for a in all_answers) / max(1, len(all_answers)), 1)
        rel_score = round(sum(a.relevance_score for a in all_answers) / max(1, len(all_answers)), 1)
        comp_score = round(sum(a.completeness_score for a in all_answers) / max(1, len(all_answers)), 1)
        interview.overall_score = avg_score

        if avg_score == 0:
            strengths = ["Attended the interview session"]
            weaknesses = ["No verbal or typed answers were submitted"]
            recs = ["Ensure your microphone or typing input is active during the question"]
        elif avg_score >= 70:
            strengths = ["Strong grasp over resume skills and technical fundamentals", "Structured responses"]
            weaknesses = ["Elaborate further on trade-offs and edge cases"]
            recs = ["Structure behavioral responses using the STAR method", "Provide exact quantitative metrics"]
        else:
            strengths = ["Addressed core topics"]
            weaknesses = ["Responses lacked detail and technical depth"]
            recs = ["Structure answers thoroughly", "Highlight relevant project tools and design choices"]

        report = Report(
            interview_id=interview.id,
            overall_score=avg_score,
            technical_score=tech_score,
            communication_score=comm_score,
            speech_score=comp_score,
            presentation_score=rel_score,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recs
        )
        db.add(report)
        db.commit()
        return {"completed": True, "interview_id": interview.id}

    resume = db.query(Resume).filter(Resume.id == interview.resume_id).first()
    skills = [s.skill_name for s in resume.skills] if (resume and resume.skills) else []
    projects = [{"name": p.project_name, "description": p.description} for p in resume.projects] if (resume and resume.projects) else []

    all_prev_questions = db.query(Question).filter(Question.interview_id == interview.id).all()
    history = [{"question": q.question_text, "topic": q.topic, "answer": (q.answer.transcript if q.answer else ""), "score": (q.answer.overall_score if q.answer else 0.0)} for q in all_prev_questions if q.answer]

    next_q = DynamicZeroShotAIEngine.generate_question(
        role=interview.role,
        skills=skills,
        projects=projects,
        history=history,
        current_difficulty=question.difficulty
    )

    next_question = Question(
        interview_id=interview.id,
        question_text=next_q.get("question") or f"Can you explain your technical approach and challenges faced in {interview.role}?",
        question_type=next_q.get("type") or "Adaptive Follow-up",
        topic=next_q.get("topic") or "Dynamic Assessment",
        difficulty=next_q.get("difficulty") or "Medium",
        sequence_number=question.sequence_number + 1
    )
    db.add(next_question)
    db.commit()
    db.refresh(next_question)

    return {
        "completed": False,
        "interview_id": interview.id,
        "question_id": next_question.id,
        "sequence_number": next_question.sequence_number,
        "total_questions": interview.total_questions,
        "question_text": next_question.question_text,
        "topic": next_question.topic,
        "difficulty": next_question.difficulty
    }
