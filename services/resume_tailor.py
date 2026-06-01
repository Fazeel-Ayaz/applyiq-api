import os
import json
import anthropic
from models import (
    JobObject,
    UserProfile,
    ResumeTailorResponse,
    ResumeObject,
    TailoredExperience,
    PersonalInfo,
    Education,
)


async def tailor_resume(
    job: JobObject, profile: UserProfile, base_resume_text: str
) -> ResumeTailorResponse:
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    profile_text = json.dumps(profile.model_dump(), indent=2)
    job_text = json.dumps(job.model_dump(), indent=2)

    prompt = f"""You are an expert resume writer and ATS optimization specialist.

## Job Posting
{job_text}

## Candidate Profile
{profile_text}

## Current Resume Text
{base_resume_text}

## Your Tasks

### 1. Extract ATS Keywords
Identify the top 10 most important ATS keywords from the job description.

### 2. Tailor the Resume
Rewrite the candidate's experience bullets using the Google XYZ formula:
"Accomplished [X] as measured by [Y], by doing [Z]"

Rules:
- ONLY reframe and reorder content that exists in the candidate's actual profile
- NEVER invent achievements, metrics, or experience the candidate doesn't have
- Inject ATS keywords naturally where the candidate genuinely has that skill/experience
- Select the most relevant experience sections for this specific role
- Keep it truthful — rephrase for impact, don't fabricate

### 3. Generate a Professional Summary
Write a 2-3 sentence summary highlighting the candidate's fit for this role, using only verified experience.

### 4. Write a Cover Letter
3 paragraphs:
- Hook: Why this role and company excite the candidate (use real background)
- Proof: 2-3 specific achievements from their profile that match key requirements
- Close: Enthusiasm and call to action

Return a JSON object with exactly this structure:
{{
  "tailored_resume": {{
    "personal_info": {{
      "name": "",
      "email": "",
      "phone": "",
      "location": "",
      "linkedin": ""
    }},
    "summary": "professional summary",
    "experience": [
      {{
        "title": "Job Title",
        "company": "Company Name",
        "start_date": "Start",
        "end_date": "End",
        "bullets": ["XYZ bullet 1", "XYZ bullet 2"]
      }}
    ],
    "education": [
      {{
        "degree": "",
        "institution": "",
        "start_date": "",
        "end_date": "",
        "gpa": ""
      }}
    ],
    "skills": ["skill1", "skill2"]
  }},
  "cover_letter": "Full cover letter text",
  "keywords_injected": ["keyword1", "keyword2"]
}}

Populate personal_info from the candidate profile. Return ONLY the JSON object."""

    message = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(response_text)

    resume_data = data["tailored_resume"]
    tailored_resume = ResumeObject(
        personal_info=PersonalInfo(**resume_data["personal_info"]),
        summary=resume_data["summary"],
        experience=[TailoredExperience(**e) for e in resume_data["experience"]],
        education=[Education(**e) for e in resume_data["education"]],
        skills=resume_data["skills"],
    )

    return ResumeTailorResponse(
        tailored_resume=tailored_resume,
        cover_letter=data["cover_letter"],
        keywords_injected=data["keywords_injected"],
    )
