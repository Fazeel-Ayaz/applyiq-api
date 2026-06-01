import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from models import ResumeTailorRequest, ResumeTailorResponse, ResumeObject
from services.resume_tailor import tailor_resume
from services.pdf_generator import generate_resume_pdf

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/tailor", response_model=ResumeTailorResponse)
async def tailor_resume_endpoint(req: ResumeTailorRequest):
    try:
        result = await tailor_resume(req.job, req.profile, req.base_resume_text)
        return result
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=422,
            detail={"error": "AI response error", "detail": "Could not parse tailoring response"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Resume tailoring failed", "detail": str(e)},
        )


@router.post("/generate-pdf")
async def generate_pdf_endpoint(resume: ResumeObject):
    try:
        pdf_bytes = generate_resume_pdf(resume)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=resume.pdf"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "PDF generation failed", "detail": str(e)},
        )
