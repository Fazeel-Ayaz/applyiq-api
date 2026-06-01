from pydantic import BaseModel, Field
from typing import Optional


class JobSearchRequest(BaseModel):
    keywords: str
    location: str = ""
    remote_only: bool = False
    experience_level: str = ""
    limit: int = Field(default=20, le=50)


class JobSearchByURLRequest(BaseModel):
    url: str


class JobObject(BaseModel):
    id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    source: str
    muse_culture_data: Optional[dict] = None


class PersonalInfo(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""


class Experience(BaseModel):
    title: str = ""
    company: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    bullets: list[str] = []


class Education(BaseModel):
    degree: str = ""
    institution: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""


class UserProfile(BaseModel):
    personal_info: PersonalInfo = PersonalInfo()
    experience: list[Experience] = []
    education: list[Education] = []
    skills: list[str] = []
    summary: str = ""


class JobScoreRequest(BaseModel):
    job: JobObject
    profile: UserProfile


class JobScoreResponse(BaseModel):
    score: int
    reasons: list[str]
    green_flags: list[str]
    red_flags: list[str]
    recommendation: str


class ResumeTailorRequest(BaseModel):
    job: JobObject
    profile: UserProfile
    base_resume_text: str


class TailoredExperience(BaseModel):
    title: str
    company: str
    start_date: str
    end_date: str
    bullets: list[str]


class ResumeObject(BaseModel):
    personal_info: PersonalInfo
    summary: str
    experience: list[TailoredExperience]
    education: list[Education]
    skills: list[str]


class ResumeTailorResponse(BaseModel):
    tailored_resume: ResumeObject
    cover_letter: str
    keywords_injected: list[str]


class GmailSyncRequest(BaseModel):
    gmail_access_token: str
    companies: list[str]


class GmailUpdate(BaseModel):
    company: str
    role: str
    new_status: str
    email_subject: str


class GmailSyncResponse(BaseModel):
    updates: list[GmailUpdate]


class ErrorResponse(BaseModel):
    error: str
    detail: str
