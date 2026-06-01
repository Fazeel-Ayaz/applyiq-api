import os
import httpx
from typing import Optional
from models import JobObject

JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
MUSE_API_KEY = os.getenv("MUSE_API_KEY")

JSEARCH_BASE = "https://jsearch.p.rapidapi.com/search"
ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
MUSE_BASE = "https://www.themuse.com/api/public/jobs"

# Maps experience level into natural language query terms
# JSearch does not have a seniority filter — we fold it into the query string
EXPERIENCE_QUERY_MAP = {
    "entry": "junior entry-level",
    "mid": "mid-level",
    "senior": "senior",
    "lead": "lead principal",
    "any": "",
}

# Maps country names to Adzuna country codes
ADZUNA_COUNTRY_MAP = {
    "united states": "us",
    "usa": "us",
    "us": "us",
    "united kingdom": "gb",
    "uk": "gb",
    "gb": "gb",
    "australia": "au",
    "canada": "ca",
    "germany": "de",
    "france": "fr",
    "india": "in",
    "brazil": "br",
    "netherlands": "nl",
    "new zealand": "nz",
    "singapore": "sg",
    "south africa": "za",
    "poland": "pl",
    "russia": "ru",
    "united arab emirates": "ae",
    "uae": "ae",
}


def _dedup(jobs: list[dict]) -> list[dict]:
    """Deduplicate jobs by (company, title) pair, keeping first occurrence."""
    seen = set()
    result = []
    for job in jobs:
        key = (job.get("company", "").lower().strip(), job.get("title", "").lower().strip())
        if key not in seen:
            seen.add(key)
            result.append(job)
    return result


async def _enrich_with_muse(jobs: list[dict]) -> list[dict]:
    """
    Enrich jobs with The Muse company culture data where available.
    Matches by company name. Silently skips if Muse API is unavailable.
    """
    if not MUSE_API_KEY:
        return jobs

    company_names = list({j.get("company", "") for j in jobs if j.get("company")})
    muse_data: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=10) as client:
        for company in company_names[:10]:  # cap at 10 to avoid rate limits
            try:
                resp = await client.get(
                    MUSE_BASE,
                    params={"company": company, "api_key": MUSE_API_KEY, "page": 1},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    if results:
                        muse_data[company.lower()] = {
                            "culture_summary": results[0].get("contents", "")[:300],
                            "muse_url": results[0].get("refs", {}).get("landing_page", ""),
                        }
            except Exception:
                continue  # silently skip on any error

    for job in jobs:
        company_key = job.get("company", "").lower()
        if company_key in muse_data:
            job["muse_culture_data"] = muse_data[company_key]

    return jobs


async def search_jsearch(
    keywords: str,
    location: str,
    experience_level: str = "any",
    remote_only: bool = False,
    limit: int = 10,
) -> list[dict]:
    """
    Search jobs via JSearch (RapidAPI).
    experience_level is folded into the query string — NOT sent as employment_types.
    employment_types is a job-type filter (FULLTIME/PARTTIME), not a seniority filter.
    """
    if not JSEARCH_API_KEY:
        return []

    experience_term = EXPERIENCE_QUERY_MAP.get(experience_level.lower(), "")
    query_parts = [keywords]
    if experience_term:
        query_parts.append(experience_term)
    if location:
        query_parts.append(f"in {location}")
    query = " ".join(query_parts).strip()

    params = {
        "query": query,
        "num_pages": 1,
        "page": 1,
        "employment_types": "FULLTIME",  # always request full-time roles
    }

    if remote_only:
        params["remote_jobs_only"] = "true"

    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(JSEARCH_BASE, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            raw_jobs = data.get("data", [])
    except Exception:
        return []

    jobs = []
    for job in raw_jobs[:limit]:
        jobs.append(
            {
                "id": job.get("job_id", ""),
                "title": job.get("job_title", ""),
                "company": job.get("employer_name", ""),
                "location": f"{job.get('job_city', '')} {job.get('job_country', '')}".strip(),
                "url": job.get("job_apply_link", ""),
                "description": job.get("job_description", "")[:2000],
                "source": "jsearch",
            }
        )

    return jobs


async def search_adzuna(
    keywords: str,
    location: str,
    experience_level: str = "any",
    remote_only: bool = False,
    limit: int = 10,
) -> list[dict]:
    """
    Search jobs via Adzuna API.
    Falls back gracefully if country code not found or API unavailable.
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []

    # Adzuna requires a country code in the URL path
    country_code = ADZUNA_COUNTRY_MAP.get(location.lower().strip(), "us")

    # Fold experience level into query string
    experience_term = EXPERIENCE_QUERY_MAP.get(experience_level.lower(), "")
    query_parts = [keywords]
    if experience_term:
        query_parts.append(experience_term)
    query = " ".join(query_parts).strip()

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query,
        "results_per_page": limit,
        "page": 1,
        "content-type": "application/json",
    }

    if location:
        params["where"] = location

    if remote_only:
        params["what"] = f"{query} remote"

    url = f"{ADZUNA_BASE}/{country_code}/search/1"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            raw_jobs = data.get("results", [])
    except Exception:
        return []

    jobs = []
    for job in raw_jobs[:limit]:
        jobs.append(
            {
                "id": job.get("id", ""),
                "title": job.get("title", ""),
                "company": job.get("company", {}).get("display_name", ""),
                "location": job.get("location", {}).get("display_name", ""),
                "url": job.get("redirect_url", ""),
                "description": job.get("description", "")[:2000],
                "source": "adzuna",
            }
        )

    return jobs


async def search_jobs(
    keywords: str,
    location: str,
    remote_only: bool = False,
    experience_level: str = "any",
    limit: int = 15,
) -> list[JobObject]:
    """
    Main job discovery function.
    Queries JSearch first, falls back to Adzuna, deduplicates, enriches with Muse.
    """
    jsearch_jobs = await search_jsearch(
        keywords=keywords,
        location=location,
        experience_level=experience_level,
        remote_only=remote_only,
        limit=limit,
    )

    adzuna_jobs = await search_adzuna(
        keywords=keywords,
        location=location,
        experience_level=experience_level,
        remote_only=remote_only,
        limit=limit,
    )

    combined = _dedup(jsearch_jobs + adzuna_jobs)
    enriched = await _enrich_with_muse(combined)

    return [JobObject(**job) for job in enriched[:limit]]


async def fetch_job_from_url(url: str) -> dict:
    """
    Fetch a job posting from a direct URL.
    Returns raw HTML text for Claude to extract structured data from.
    """
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ApplyIQ/1.0)"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return {"url": url, "html": resp.text[:8000], "status": "ok"}
    except Exception as e:
        return {"url": url, "html": "", "status": "error", "error": str(e)}
