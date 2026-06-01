import os
import re
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import jobs, profile, resume, gmail

app = FastAPI(
    title="ApplyIQ API",
    version="1.0.0",
    description="AI-powered job search and application backend",
)

frontend_url = os.getenv("FRONTEND_URL", "")
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]
if frontend_url:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*.lovable(?:project)?\.(?:app|com)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(profile.router)
app.include_router(resume.router)
app.include_router(gmail.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )