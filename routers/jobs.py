import os
import json
import anthropic
import httpx
from fastapi import APIRouter, HTTPException
from models import (
    JobSearchRequest,
    JobSearchByURLRequest,
    JobObject,
    JobScoreRequest,
    JobScoreResponse,
)
from services.job_discovery import search_jobs
from services.job_scorer import score_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/search", response_model=list[JobObject])
async def search_jobs_endpoint(req: JobSearchRequest):
    try:
        jobs = await search_jobs(
            keywords=req.keywords,
            location=req.location,
            remote_only=req.remote_only,
            experience_level=req.experience_level,
            limit=req.limit,
        )
        return jobs
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail={"error": "Job search API error", "detail": str(e)},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Job search failed", "detail": str(e)})


@router.post("/search-by-url", response_model=JobObject)
async def search_by_url_endpoint(req: JobSearchByURLRequest):
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(req.url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; ApplyIQ/1.0)"
            })
            resp.raise_for_status()
            page_html = resp.text[:15000]

        ai_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = await ai_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"""Extract job posting details from this HTML. Return a JSON object with:
- title: job title
- company: company name
- location: job location
- description: full job description text
- requirements: key requirements as part of description

HTML content:
{page_html}

Return ONLY a JSON object with keys: title, company, location, description. No markdown.""",
            }],
        )

        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        data = json.loads(response_text)

        import hashlib
        job_id = hashlib.md5(f"{data['company']}|{data['title']}".encode()).hexdigest()[:12]

        return JobObject(
            id=job_id,
            title=data.get("title", ""),
            company=data.get("company", ""),
            location=data.get("location", ""),
            url=req.url,
            description=data.get("description", ""),
            source="url_extract",
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=422,
            detail={"error": "Parse error", "detail": "Could not extract job details from the URL"},
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail={"error": "Failed to fetch URL", "detail": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "URL extraction failed", "detail": str(e)},
        )


@router.post("/score", response_model=JobScoreResponse)
async def score_job_endpoint(req: JobScoreRequest):
    try:
        result = await score_job(req.job, req.profile)
        return result
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=422,
            detail={"error": "AI response error", "detail": "Could not parse scoring response"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Job scoring failed", "detail": str(e)},
        )
