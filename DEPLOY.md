# ApplyIQ API — Railway Deployment Guide

## Prerequisites
- A [Railway](https://railway.app) account
- The [Railway CLI](https://docs.railway.app/develop/cli) installed (optional but helpful)
- A GitHub repository with this code pushed

## Step 1: Create a Railway Project

1. Go to [railway.app/new](https://railway.app/new)
2. Click **"Deploy from GitHub Repo"**
3. Select your repository containing the `applyiq-api` directory
4. Railway will auto-detect Python and use the `railway.toml` config

## Step 2: Set the Root Directory

If your repo has other folders (e.g., a frontend), set the root directory:

1. Go to your service **Settings** tab
2. Under **Root Directory**, enter: `applyiq-api`

## Step 3: Set Environment Variables

Go to your service's **Variables** tab and add each of these:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Claude API key (starts with `sk-ant-`) |
| `JSEARCH_API_KEY` | RapidAPI key for JSearch |
| `ADZUNA_APP_ID` | Adzuna application ID |
| `ADZUNA_APP_KEY` | Adzuna application key |
| `MUSE_API_KEY` | The Muse API key |
| `AFFINDA_API_KEY` | Affinda API key for resume parsing |
| `SUPABASE_URL` | Your Supabase project URL (e.g., `https://xxx.supabase.co`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (from Settings > API) |
| `FRONTEND_URL` | Your Lovable app URL (e.g., `https://yourapp.lovable.app`) |

> **Tip:** You can bulk-add variables by pasting your `.env` file contents into the RAW Editor.

## Step 4: Deploy

Railway auto-deploys on every push to your main branch. To trigger a manual deploy:

1. Go to the **Deployments** tab
2. Click **"Deploy"** or push a commit

## Step 5: Get Your API URL

After deployment succeeds:

1. Go to **Settings** > **Networking**
2. Click **"Generate Domain"** to get a public URL
3. Your API will be at: `https://your-service.up.railway.app`

## Step 6: Verify

```bash
curl https://your-service.up.railway.app/health
```

Expected response:
```json
{"status": "ok", "version": "1.0.0"}
```

## Step 7: Update Your Frontend

Set your Lovable frontend's API base URL to the Railway domain:

```
https://your-service.up.railway.app
```

Then update the `FRONTEND_URL` variable in Railway to your actual Lovable app URL for CORS to work.

## API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/profile/parse-resume` | Upload and parse a resume (PDF/DOCX) |
| POST | `/jobs/search` | Search jobs across JSearch + Adzuna |
| POST | `/jobs/search-by-url` | Extract job details from a URL |
| POST | `/jobs/score` | AI-score a job match (0-100) |
| POST | `/resume/tailor` | AI-tailor resume + cover letter for a job |
| POST | `/resume/generate-pdf` | Generate a PDF from tailored resume |
| POST | `/gmail/sync` | Sync application statuses from Gmail |

## Troubleshooting

- **Build fails**: Check that `requirements.txt` is in the root directory (or the configured root)
- **CORS errors**: Ensure `FRONTEND_URL` matches your Lovable app URL exactly (including `https://`)
- **API key errors**: Double-check each variable is set correctly in Railway's Variables tab
- **Timeout on resume parse**: Affinda can take up to 60 seconds for large files — this is normal
