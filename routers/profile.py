from fastapi import APIRouter, UploadFile, File, HTTPException
from models import UserProfile
from services.resume_parser import parse_resume

router = APIRouter(prefix="/profile", tags=["profile"])

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/parse-resume", response_model=UserProfile)
async def parse_resume_endpoint(file: UploadFile = File(...)):
    if file.content_type and file.content_type not in ALLOWED_TYPES:
        ext = file.filename.split(".")[-1].lower() if file.filename else ""
        if ext not in ("pdf", "docx"):
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid file type", "detail": "Only PDF and DOCX files are accepted"},
            )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail={"error": "File too large", "detail": "Maximum file size is 10MB"},
        )

    try:
        profile = await parse_resume(file_bytes, file.filename or "resume.pdf")
        return profile
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Resume parsing failed", "detail": str(e)},
        )
