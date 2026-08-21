import os
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routers import auth, resume, interview, report

# Initialize database schemas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title='AI Interviewer API',
    description='Zero-Shot Dynamic Interview Performance Analyzer',
    version='1.0.0'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/', status_code=status.HTTP_200_OK)
@app.head('/', status_code=status.HTTP_200_OK)
def health_check():
    return {'status': 'online', 'message': 'AI Interviewer 24/7 Engine Active'}

app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(interview.router)
app.include_router(report.router)
