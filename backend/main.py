import os
from fastapi import FastAPI, Response, status
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

app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(interview.router)
app.include_router(report.router)

# Mount and serve frontend static files
if os.path.exists('frontend'):
    app.mount('/static', StaticFiles(directory='frontend'), name='static')

@app.get('/')
@app.head('/')
def serve_frontend():
    if os.path.exists('frontend/index.html'):
        return FileResponse('frontend/index.html')
    return {'status': 'online', 'message': 'AI Interviewer 24/7 Engine Active'}
