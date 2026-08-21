from pydantic import BaseModel, EmailStr
from typing import List, Optional

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_name: str
    user_email: str

class InterviewCreate(BaseModel):
    role: str = "Data Scientist"
    difficulty: str = "Medium"
    total_questions: int = 5

class AnswerSubmit(BaseModel):
    interview_id: int
    question_id: int
    transcript: str
    duration: float = 30.0
