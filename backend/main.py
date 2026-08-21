import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# 1. Include Backend API Routers under /api
app.include_router(auth.router, prefix='/api')
app.include_router(resume.router, prefix='/api')
app.include_router(interview.router, prefix='/api')
app.include_router(report.router, prefix='/api')

# 2. Serve Static Frontend Files
if os.path.exists('frontend'):
    app.mount('/', StaticFiles(directory='frontend', html=True), name='frontend')
