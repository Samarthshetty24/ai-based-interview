from sqlalchemy import Column, Integer, String, Text
from backend.database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    resume_text = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)
