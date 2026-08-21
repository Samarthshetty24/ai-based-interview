import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.database import engine, Base
from backend.routers import auth, resume, interview, report

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

app.include_router(auth.router, prefix='/api/auth', tags=['Auth'])
app.include_router(resume.router, prefix='/api/resume', tags=['Resume'])
app.include_router(interview.router, prefix='/api/interview', tags=['Interview'])
app.include_router(report.router, prefix='/api/report', tags=['Report'])

if os.path.exists('frontend'):
    app.mount('/', StaticFiles(directory='frontend', html=True), name='frontend')
