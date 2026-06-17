# ApplyIQ

**AI-powered job application copilot.** ApplyIQ finds roles, scores them against your experience, tailors your resume per application, and pre-fills every ATS form — so you apply smarter, not more.

---

## What It Does

Most job seekers send 200+ applications to get one offer. The bottleneck isn't the submit button — it's everything before it: finding the right roles, tailoring a resume for each one, and filling the same form fields 50 times over.

ApplyIQ compresses that process from hours to minutes:

- **Job Discovery** — searches across LinkedIn, Indeed, Glassdoor, and ZipRecruiter simultaneously via JSearch and Adzuna
- **AI Match Scoring** — scores every role 0–100 against your actual experience with transparent reasoning, green flags, and red flags
- **Resume Tailoring** — rewrites your resume for each role using the Google XYZ formula, injecting real ATS keywords without fabricating experience
- **Cover Letter Generation** — produces a targeted 3-paragraph cover letter per role
- **One-Page PDF Export** — clean, ATS-ready PDF that auto-scales to fit one page
- **Quick Copy Panel** — pre-fills name, phone, email, LinkedIn, work authorization, and EEO fields as copyable chips for any ATS form
- **Job Tracker** — Kanban pipeline from Discovered → Applied → Offer with status tracking
- **Gmail Sync** — detects responses, interview invites, and rejections automatically

---

## Architecture

```
Frontend (Lovable)          Backend (Railway)           External APIs
──────────────────          ─────────────────           ─────────────
React + Tailwind      →     FastAPI (Python)       →    JSearch (RapidAPI)
Supabase Auth               /jobs/search                Adzuna
Supabase DB                 /jobs/score                 The Muse
Supabase Storage            /jobs/search-by-url         Claude API
                            /resume/tailor              Affinda → Claude
                            /resume/generate-pdf
                            /profile/parse-resume
                            /gmail/sync
```

---

## Tech Stack

**Frontend**
- React + Vite
- Tailwind CSS + shadcn/ui
- Supabase (auth, database, storage)
- Hosted on Lovable

**Backend**
- Python 3.11 + FastAPI
- Anthropic Claude API (`claude-sonnet-4-5`) for scoring, tailoring, parsing
- ReportLab for PDF generation
- Hosted on Railway

**Job Data**
- JSearch via RapidAPI — LinkedIn, Indeed, Glassdoor, ZipRecruiter
- Adzuna API — additional global coverage
- The Muse API — company culture enrichment

---

## Supported Markets

Strong coverage in: **UAE, US, UK, Canada, Australia, India, Singapore**

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend Setup

```bash
git clone https://github.com/Fazeel-Ayaz/applyiq-api
cd applyiq-api
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env
uvicorn main:app --reload
```

### Environment Variables

```
ANTHROPIC_API_KEY=
JSEARCH_API_KEY=
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
MUSE_API_KEY=
AFFINDA_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
FRONTEND_URL=
```

### API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/jobs/search` | Search jobs by keyword + location |
| POST | `/jobs/search-by-url` | Extract job from URL |
| POST | `/jobs/score` | Score a job against a profile |
| POST | `/resume/tailor` | Tailor resume + generate cover letter |
| POST | `/resume/generate-pdf` | Generate one-page PDF |
| POST | `/profile/parse-resume` | Parse uploaded resume via Claude |
| POST | `/gmail/sync` | Sync Gmail for application responses |

---

## Deployment

Backend is deployed on Railway. See [DEPLOY.md](./DEPLOY.md) for step-by-step instructions.

Frontend is deployed on Lovable and connects to the Railway backend via `VITE_API_URL`.

---

## Roadmap

- [ ] Browser extension for ATS autofill
- [ ] European job board coverage (StepStone, Xing, EURES)
- [ ] Interview preparation module
- [ ] Referral network surfacing (warm intro finder)
- [ ] Application follow-up reminders
- [ ] Response rate analytics per resume version

---

## Built By

Fazeel Ayaz — Growth Marketer & Vibe Coder  
Built for the Vibe Coding World Cup

[LinkedIn](https://linkedin.com/in/fazeel-ayaz/) · [GitHub](https://github.com/Fazeel-Ayaz)
