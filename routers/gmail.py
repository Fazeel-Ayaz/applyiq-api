import httpx
from fastapi import APIRouter, HTTPException
from models import GmailSyncRequest, GmailSyncResponse, GmailUpdate

router = APIRouter(prefix="/gmail", tags=["gmail"])

STATUS_KEYWORDS = {
    "Offer": [
        "offer letter", "we are pleased to offer", "congratulations on your offer",
        "compensation package", "start date", "offer of employment",
    ],
    "Interview Scheduled": [
        "interview", "schedule a call", "phone screen", "video interview",
        "meet the team", "interview invitation", "calendly",
    ],
    "Round 2": [
        "next round", "second round", "final round", "onsite interview",
        "technical interview", "panel interview", "take-home",
    ],
    "Rejected": [
        "unfortunately", "not moving forward", "other candidates",
        "we regret", "position has been filled", "not selected",
        "will not be proceeding", "decided not to",
    ],
    "Confirmation Received": [
        "application received", "thank you for applying", "we received your application",
        "application confirmation", "successfully submitted",
    ],
}

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


@router.post("/sync", response_model=GmailSyncResponse)
async def sync_gmail_endpoint(req: GmailSyncRequest):
    if not req.gmail_access_token or not req.companies:
        raise HTTPException(
            status_code=400,
            detail={"error": "Missing parameters", "detail": "gmail_access_token and companies are required"},
        )

    headers = {"Authorization": f"Bearer {req.gmail_access_token}"}
    updates: list[GmailUpdate] = []

    async with httpx.AsyncClient(timeout=15) as client:
        for company in req.companies:
            try:
                query = f"from:{company} OR subject:{company}"
                resp = await client.get(
                    f"{GMAIL_API_BASE}/messages",
                    headers=headers,
                    params={"q": query, "maxResults": "10"},
                )
                if resp.status_code == 401:
                    raise HTTPException(
                        status_code=401,
                        detail={"error": "Gmail auth expired", "detail": "Please re-authenticate with Google"},
                    )
                resp.raise_for_status()
                messages = resp.json().get("messages", [])

                for msg_ref in messages:
                    msg_resp = await client.get(
                        f"{GMAIL_API_BASE}/messages/{msg_ref['id']}",
                        headers=headers,
                        params={"format": "metadata", "metadataHeaders": ["Subject", "From"]},
                    )
                    if msg_resp.status_code != 200:
                        continue

                    msg_data = msg_resp.json()
                    headers_list = msg_data.get("payload", {}).get("headers", [])
                    subject = ""
                    for h in headers_list:
                        if h["name"].lower() == "subject":
                            subject = h["value"]
                            break

                    snippet = msg_data.get("snippet", "").lower()
                    subject_lower = subject.lower()
                    combined_text = f"{subject_lower} {snippet}"

                    status = _detect_status(combined_text)
                    if status:
                        updates.append(GmailUpdate(
                            company=company,
                            role=_extract_role(subject),
                            new_status=status,
                            email_subject=subject,
                        ))
                        break

            except HTTPException:
                raise
            except Exception:
                continue

    return GmailSyncResponse(updates=updates)


def _detect_status(text: str) -> str | None:
    for status in ["Offer", "Round 2", "Interview Scheduled", "Rejected", "Confirmation Received"]:
        keywords = STATUS_KEYWORDS[status]
        for keyword in keywords:
            if keyword in text:
                return status
    return None


def _extract_role(subject: str) -> str:
    noise = [
        "re:", "fwd:", "application", "update", "status",
        "your", "for", "the", "at", "–", "-", "|",
    ]
    parts = subject.split()
    cleaned = [p for p in parts if p.lower().strip(":-") not in noise]
    return " ".join(cleaned[:6]) if cleaned else subject
