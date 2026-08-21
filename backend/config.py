from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "AI Interview Analyzer"
    APP_ENV: str = "development"
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    DATABASE_URL: str = "sqlite:///./interview_analyzer.db"
    SECRET_KEY: str = "super_secret_jwt_key_bsc_data_science_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]
    GEMINI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()