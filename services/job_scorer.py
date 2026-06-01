import os
import json
import anthropic
from models import JobObject, UserProfile, JobScoreResponse


async def score_job(job: JobObject, profile: UserProfile) -> JobScoreResponse:
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    profile_text = json.dumps(profile.model_dump(), indent=2)
    job_text = json.dumps(job.model_dump(), indent=2)

    prompt = f"""You are an expert career advisor. Score how well this candidate matches the job posting.

## Job Posting
{job_text}

## Candidate Profile
{profile_text}

## Scoring Criteria (weight each equally):
1. Title/role match — does their experience align with this role?
2. Required skills overlap — how many required skills does the candidate have?
3. Experience level fit — are they too junior, too senior, or right?
4. Location/remote match — can they work where the job requires?
5. Seniority alignment — does career trajectory make sense?

IMPORTANT: Only evaluate based on what exists in the candidate profile. Never assume or fabricate experience they don't have.

Return a JSON object with exactly this structure:
{{
  "score": <0-100 integer>,
  "reasons": ["reason 1", "reason 2", "reason 3"],
  "green_flags": ["positive signal 1", "positive signal 2"],
  "red_flags": ["concern 1", "concern 2"],
  "recommendation": "<one of: apply, consider, skip>"
}}

Rules for recommendation:
- score >= 70: "apply"
- score 40-69: "consider"
- score < 40: "skip"

Return ONLY the JSON object, no markdown formatting."""

    message = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(response_text)
    return JobScoreResponse(**data)
