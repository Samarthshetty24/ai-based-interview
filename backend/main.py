import os
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.database import engine, Base
from backend.routers import auth, resume, interview, report

# Drop outdated tables and initialize fresh schema with all columns
try:
    Base.metadata.create_all(bind=engine)
    # If using SQLite and column is missing, recreate tables
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
        column_names = [col[1] for col in result]
        if "hashed_password" not in column_names:
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
except Exception:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Interviewer API",
    description="Zero-Shot Dynamic Interview Performance Analyzer",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Server Error: {str(exc)}"}
    )

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(resume.router, prefix="/api/resume", tags=["Resume"])
app.include_router(interview.router, prefix="/api/interview", tags=["Interview"])
app.include_router(report.router, prefix="/api/report", tags=["Report"])

if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
