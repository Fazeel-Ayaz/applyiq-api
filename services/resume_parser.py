import os
import json
import base64
import anthropic
from models import UserProfile, PersonalInfo, Experience, Education


async def parse_resume(file_bytes: bytes, filename: str) -> UserProfile:
    """
    Parse a resume PDF or DOCX using Claude.
    Replaces Affinda — no external dependency needed beyond the Anthropic API.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    client = anthropic.AsyncAnthropic(api_key=api_key)

    # Encode file as base64
    file_b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    # Determine media type
    fn_lower = filename.lower()
    if fn_lower.endswith(".pdf"):
        media_type = "application/pdf"
    else:
        # For DOCX and other formats, ask Claude to interpret as text
        media_type = "application/pdf"  # fallback — Claude handles PDFs best

    prompt = """Extract all information from this resume and return a JSON object with exactly this structure:

{
  "name": "full name",
  "email": "email address",
  "phone": "phone number",
  "location": "city, country or full address",
  "linkedin": "linkedin URL if present, else empty string",
  "summary": "professional summary or objective if present, else empty string",
  "skills": ["skill1", "skill2", "skill3"],
  "experience": [
    {
      "title": "job title",
      "company": "company name",
      "start_date": "start date as written",
      "end_date": "end date as written or Present",
      "description": "full description text",
      "bullets": ["bullet 1", "bullet 2"]
    }
  ],
  "education": [
    {
      "degree": "degree name",
      "institution": "university or school name",
      "start_date": "start date",
      "end_date": "end date",
      "gpa": "GPA if present, else empty string"
    }
  ]
}

Rules:
- Return ONLY the JSON object, no markdown, no backticks, no explanation
- Extract every work experience entry, even short ones
- Extract every skill mentioned anywhere in the resume
- If a field is not present, use an empty string or empty array
- For bullets, split description into individual bullet points"""

    message = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": file_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text.strip()

    # Strip markdown fences if present
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(response_text)

    personal_info = PersonalInfo(
        name=data.get("name", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        location=data.get("location", ""),
        linkedin=data.get("linkedin", ""),
    )

    experience = []
    for exp in data.get("experience", []):
        experience.append(
            Experience(
                title=exp.get("title", ""),
                company=exp.get("company", ""),
                start_date=exp.get("start_date", ""),
                end_date=exp.get("end_date", ""),
                description=exp.get("description", ""),
                bullets=exp.get("bullets", []),
            )
        )

    education = []
    for edu in data.get("education", []):
        education.append(
            Education(
                degree=edu.get("degree", ""),
                institution=edu.get("institution", ""),
                start_date=edu.get("start_date", ""),
                end_date=edu.get("end_date", ""),
                gpa=edu.get("gpa", ""),
            )
        )

    return UserProfile(
        personal_info=personal_info,
        experience=experience,
        education=education,
        skills=data.get("skills", []),
        summary=data.get("summary", ""),
    )
