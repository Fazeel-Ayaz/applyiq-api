import os
import httpx
from models import UserProfile, PersonalInfo, Experience, Education


AFFINDA_BASE = "https://api.affinda.com/v3"


async def parse_resume(file_bytes: bytes, filename: str) -> UserProfile:
    api_key = os.getenv("AFFINDA_API_KEY", "")

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    files = {
        "file": (filename, file_bytes),
    }
    data = {
        "wait": "true",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{AFFINDA_BASE}/documents",
            headers=headers,
            files=files,
            data=data,
        )
        resp.raise_for_status()
        result = resp.json()

    parsed = result.get("data", {})

    name_data = parsed.get("name", {})
    personal_info = PersonalInfo(
        name=name_data.get("raw", "") if name_data else "",
        email=_first_value(parsed.get("emails", [])),
        phone=_first_value(parsed.get("phoneNumbers", [])),
        location=_get_location(parsed.get("location", {})),
        linkedin=_find_linkedin(parsed.get("websites", [])),
    )

    experience = []
    for exp in parsed.get("workExperience", []):
        dates = exp.get("dates", {}) or {}
        description = exp.get("description", "") or ""
        bullets = [b.strip() for b in description.split("\n") if b.strip()] if description else []
        experience.append(Experience(
            title=exp.get("jobTitle", "") or "",
            company=exp.get("organization", "") or "",
            start_date=dates.get("rawText", "").split(" to ")[0] if dates.get("rawText") else "",
            end_date=dates.get("rawText", "").split(" to ")[-1] if dates.get("rawText") else "",
            description=description,
            bullets=bullets,
        ))

    education = []
    for edu in parsed.get("education", []):
        dates = edu.get("dates", {}) or {}
        education.append(Education(
            degree=edu.get("accreditation", {}).get("education", "") or "",
            institution=edu.get("organization", "") or "",
            start_date=dates.get("rawText", "").split(" to ")[0] if dates.get("rawText") else "",
            end_date=dates.get("rawText", "").split(" to ")[-1] if dates.get("rawText") else "",
            gpa=edu.get("grade", {}).get("raw", "") if edu.get("grade") else "",
        ))

    skills = []
    for skill in parsed.get("skills", []):
        skill_name = skill.get("name", "") if isinstance(skill, dict) else str(skill)
        if skill_name:
            skills.append(skill_name)

    summary = parsed.get("summary", "") or ""

    return UserProfile(
        personal_info=personal_info,
        experience=experience,
        education=education,
        skills=skills,
        summary=summary,
    )


def _first_value(items: list) -> str:
    if not items:
        return ""
    item = items[0]
    if isinstance(item, str):
        return item
    return item.get("raw", "") or item.get("value", "") or ""


def _get_location(loc: dict | None) -> str:
    if not loc:
        return ""
    return loc.get("rawInput", "") or loc.get("formatted", "") or ""


def _find_linkedin(websites: list) -> str:
    for site in websites:
        url = site if isinstance(site, str) else site.get("url", "")
        if "linkedin.com" in url.lower():
            return url
    return ""
