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

# 1. Include Backend API Routers
app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(interview.router)
app.include_router(report.router)

# 2. Serve Static Frontend Files (HTML, JS, CSS, Media)
if os.path.exists('frontend'):
    app.mount('/', StaticFiles(directory='frontend', html=True), name='frontend')
