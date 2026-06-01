import os
import hashlib
import httpx
from models import JobObject


JSEARCH_BASE = "https://jsearch.p.rapidapi.com"
ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
MUSE_BASE = "https://www.themuse.com/api/public"


def _make_job_id(company: str, title: str) -> str:
    raw = f"{company.lower().strip()}|{title.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


async def search_jsearch(
    keywords: str,
    location: str,
    remote_only: bool,
    experience_level: str,
    limit: int,
) -> list[dict]:
    api_key = os.getenv("JSEARCH_API_KEY", "")
    if not api_key:
        return []

    params = {
        "query": f"{keywords} in {location}" if location else keywords,
        "num_pages": "1",
        "page": "1",
    }
    if remote_only:
        params["remote_jobs_only"] = "true"
    if experience_level:
        params["employment_types"] = experience_level

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{JSEARCH_BASE}/search", headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json().get("data", [])

    results = []
    for item in data[:limit]:
        results.append({
            "title": item.get("job_title", ""),
            "company": item.get("employer_name", ""),
            "location": item.get("job_city", "") or item.get("job_country", ""),
            "url": item.get("job_apply_link", "") or item.get("job_google_link", ""),
            "description": item.get("job_description", ""),
            "source": "jsearch",
        })
    return results


async def search_adzuna(
    keywords: str,
    location: str,
    limit: int,
) -> list[dict]:
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        return []

    country = "us"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": keywords,
        "results_per_page": str(limit),
        "content-type": "application/json",
    }
    if location:
        params["where"] = location

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{ADZUNA_BASE}/{country}/search/1", params=params
        )
        resp.raise_for_status()
        data = resp.json().get("results", [])

    results = []
    for item in data:
        results.append({
            "title": item.get("title", ""),
            "company": item.get("company", {}).get("display_name", ""),
            "location": item.get("location", {}).get("display_name", ""),
            "url": item.get("redirect_url", ""),
            "description": item.get("description", ""),
            "source": "adzuna",
        })
    return results


async def enrich_with_muse(company_name: str) -> dict | None:
    api_key = os.getenv("MUSE_API_KEY", "")
    params = {"company": company_name, "page": "1"}
    if api_key:
        params["api_key"] = api_key

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{MUSE_BASE}/companies", params=params)
            if resp.status_code != 200:
                return None
            results = resp.json().get("results", [])
            if not results:
                return None
            company = results[0]
            return {
                "name": company.get("name"),
                "description": company.get("short_name", ""),
                "industries": [i.get("name") for i in company.get("industries", [])],
                "locations": [l.get("name") for l in company.get("locations", [])],
                "size": company.get("size", {}).get("name", ""),
            }
        except Exception:
            return None


def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for job in jobs:
        key = (job["company"].lower().strip(), job["title"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


async def search_jobs(
    keywords: str,
    location: str,
    remote_only: bool,
    experience_level: str,
    limit: int,
) -> list[JobObject]:
    jsearch_results = await search_jsearch(keywords, location, remote_only, experience_level, limit)
    adzuna_results = await search_adzuna(keywords, location, limit)

    combined = jsearch_results + adzuna_results
    unique = deduplicate_jobs(combined)[:limit]

    enriched_companies: dict[str, dict | None] = {}
    jobs = []
    for item in unique:
        company = item["company"]
        if company and company not in enriched_companies:
            enriched_companies[company] = await enrich_with_muse(company)

        jobs.append(JobObject(
            id=_make_job_id(item["company"], item["title"]),
            title=item["title"],
            company=item["company"],
            location=item["location"],
            url=item["url"],
            description=item["description"],
            source=item["source"],
            muse_culture_data=enriched_companies.get(company),
        ))

    return jobs
