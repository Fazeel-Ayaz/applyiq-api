import os
import httpx
from typing import Optional
from models import JobObject

JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
MUSE_API_KEY = os.getenv("MUSE_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

JSEARCH_BASE = "https://jsearch.p.rapidapi.com/search"
ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
MUSE_BASE = "https://www.themuse.com/api/public/jobs"
SERPER_BASE = "https://google.serper.dev/jobs"

# Maps experience level into natural language query terms
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
        for company in company_names[:10]:
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
                continue

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
    """Search jobs via JSearch (RapidAPI)."""
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
        "employment_types": "FULLTIME",
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
    except Exception as e:
        print(f"JSearch error: {e}")
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
    """Search jobs via Adzuna API."""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []

    country_code = ADZUNA_COUNTRY_MAP.get(location.lower().strip(), "us")

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
    except Exception as e:
        print(f"Adzuna error: {e}")
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


async def search_serper(
    keywords: str,
    location: str,
    experience_level: str = "any",
    remote_only: bool = False,
    limit: int = 10,
) -> list[dict]:
    """
    Search jobs via Serper Google Jobs API.
    Used as fallback when JSearch + Adzuna return thin results.
    Excellent coverage for non-English markets (Germany, France, etc.)
    """
    if not SERPER_API_KEY:
        return []

    experience_term = EXPERIENCE_QUERY_MAP.get(experience_level.lower(), "")
    query_parts = [keywords]
    if experience_term:
        query_parts.append(experience_term)
    if remote_only:
        query_parts.append("remote")
    if location:
        query_parts.append(location)
    query = " ".join(query_parts).strip()

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "q": query,
        "num": limit,
    }

    # Add location as gl (country code) if we can map it
    gl_map = {
        "germany": "de",
        "france": "fr",
        "united kingdom": "gb",
        "uk": "gb",
        "united states": "us",
        "usa": "us",
        "australia": "au",
        "canada": "ca",
        "india": "in",
        "singapore": "sg",
        "united arab emirates": "ae",
        "uae": "ae",
        "netherlands": "nl",
        "spain": "es",
        "italy": "it",
    }
    gl = gl_map.get(location.lower().strip())
    if gl:
        payload["gl"] = gl

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(SERPER_BASE, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            raw_jobs = data.get("jobs", [])
    except Exception as e:
        print(f"Serper error: {e}")
        return []

    jobs = []
    for job in raw_jobs[:limit]:
        import hashlib
        job_id = hashlib.md5(
            f"{job.get('companyName', '')}|{job.get('title', '')}".encode()
        ).hexdigest()[:12]

        jobs.append(
            {
                "id": job_id,
                "title": job.get("title", ""),
                "company": job.get("companyName", ""),
                "location": job.get("location", ""),
                "url": job.get("applyLink", "") or job.get("shareLink", ""),
                "description": job.get("description", "")[:2000],
                "source": "serper",
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
    Queries JSearch, Adzuna, and Serper on every search.
    Deduplicates and enriches with Muse.
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

    serper_jobs = await search_serper(
        keywords=keywords,
        location=location,
        experience_level=experience_level,
        remote_only=remote_only,
        limit=limit,
    )

    combined = _dedup(jsearch_jobs + adzuna_jobs + serper_jobs)
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
