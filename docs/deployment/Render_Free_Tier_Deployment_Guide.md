# Risk Assessment Workbench — Render Free Tier Deployment Guide

**Target audience:** Complete beginners  
**Platform:** Render.com Free Web Service  
**Repository:** https://github.com/ebtenorio-myridius/geniushack3  
**Goal:** Get a public demo URL running with the existing Dockerfile

---

## 1. What You Will Get

- A public URL (example: `https://risk-workbench.onrender.com`)
- The app runs from the exact `Dockerfile` already in the repository
- Completely free infrastructure (with the limitations listed below)

### Important Limitations of Render Free Tier

| Limitation | What it means for you |
|------------|-----------------------|
| Sleeps after 15 minutes of no traffic | First visitor after sleep waits ~30–60 seconds |
| No persistent disk | SQLite database is wiped on every restart/sleep |
| OpenAI API key required | Live PDF extraction costs money (OpenAI billing) |

These limitations are acceptable for short demos and presentations.

---

## 2. Accounts You Need

### A. GitHub Account
1. Go to [https://github.com](https://github.com)
2. Sign up or sign in
3. Confirm you can open: [https://github.com/ebtenorio-myridius/geniushack3](https://github.com/ebtenorio-myridius/geniushack3)

### B. Render Account
1. Go to [https://render.com](https://render.com)
2. Click **Get Started** / **Sign Up**
3. Choose **Sign up with GitHub** (strongly recommended)
4. Authorize Render to access your GitHub account
5. No credit card is required for the free tier

### C. OpenAI API Key (required for live extraction)
1. Go to [https://platform.openai.com](https://platform.openai.com)
2. Sign up or sign in
3. Navigate to **API keys** → **Create new secret key**
4. Copy the key (it starts with `sk-...`)
5. Optional but recommended: Set a soft usage limit ($5–$10) to avoid surprises

---

## 3. Prepare the Repository

You have two options:

### Option A – Use the public repo directly (easiest)
Deploy straight from `ebtenorio-myridius/geniushack3`. No forking required.

### Option B – Fork the repository (recommended if you want your own copy)
1. Open [https://github.com/ebtenorio-myridius/geniushack3](https://github.com/ebtenorio-myridius/geniushack3)
2. Click the **Fork** button (top right)
3. Select your GitHub account as the destination
4. Wait a few seconds — you now have your own copy

---

## 4. Deploy on Render — Step by Step

1. Log in at [https://dashboard.render.com](https://dashboard.render.com)

2. Click the **New +** button (top right) → select **Web Service**

3. Connect the repository:
   - Select `geniushack3` (or your fork)
   - If you don’t see it, click **Configure account** / **Connect account** and grant access

4. Fill in the form **exactly** as shown:

   | Field              | Value to enter                          | Notes |
   |--------------------|-----------------------------------------|-------|
   | **Name**           | `risk-workbench` (or any name you like) | Becomes part of the URL |
   | **Region**         | Closest region to you                   | |
   | **Branch**         | `master`                                | Important — the repo uses `master`, not `main` |
   | **Root Directory** | *(leave blank)*                         | |
   | **Runtime**        | **Docker**                              | Render detects the Dockerfile |
   | **Dockerfile Path**| `./Dockerfile`                          | Default is fine |
   | **Docker Command** | *(leave blank)*                         | The Dockerfile already contains the correct CMD |
   | **Instance Type**  | **Free**                                | |

5. Scroll to **Environment Variables** and add these three:

   | Key               | Value                              |
   |-------------------|------------------------------------|
   | `OPENAI_API_KEY`  | Your real `sk-...` key             |
   | `OPENAI_MODEL`    | `gpt-4o-mini`                      |
   | `DATABASE_PATH`   | `/tmp/risk_workbench.db`           |

   > The `/tmp` path is required because the free tier has no persistent disk.

6. Click **Create Web Service**

7. Wait for the build (usually 2–5 minutes). Watch the live logs.  
   Success looks like:
   ```
   Uvicorn running on http://0.0.0.0:8000
   ```

8. When the status shows **Live**, click the URL at the top of the page.

---

## 5. Test the Deployed Application

1. Open the public URL provided by Render.
2. You should land on the login page.
3. Sign in using one of the demo accounts (type them exactly):

   | Role                    | Username          |
   |-------------------------|-------------------|
   | Product owner           | `product-owner-1` |
   | FCRM analyst            | `analyst-1`       |
   | Risk committee member   | `committee-1`     |
   |                         | `committee-2`     |
   |                         | `committee-3`     |

4. After signing in as **product-owner-1**, go to **Upload case** / intake and upload a synthetic text-based PDF.
5. Verify the health endpoint by appending `/healthz` to your URL.  
   Expected response: `{"status":"ok"}`

---

## 6. Everyday Tips

- **View logs**: Render Dashboard → your service → **Logs**
- **Redeploy**: Turn on Auto-Deploy in settings, or click **Manual Deploy**
- **Wake a sleeping service**: Simply visit the URL (first load will be slower)
- **Edit environment variables**: Dashboard → Environment → Edit → Save (triggers restart)
- **Delete the service**: Settings → Delete Web Service

---

## 7. Common Problems & Fixes

| Problem                              | Likely Cause & Solution |
|--------------------------------------|-------------------------|
| Build fails                          | Check logs. Confirm Branch is set to `master` |
| App starts but OpenAI errors appear  | Missing or incorrect `OPENAI_API_KEY` |
| Database is empty after sleep        | Expected on free tier. Just create new cases |
| “Application failed to respond”      | Service is still starting or waking up. Wait 1 minute and refresh |
| 502 / connection errors              | Free instances can be slow. Wait and retry |

---

## 8. Pre-Demo Checklist

- [ ] Render service status is **Live**
- [ ] Public URL opens successfully
- [ ] Login works with `product-owner-1`
- [ ] A sample synthetic PDF is ready to upload
- [ ] You remember the service may take 30–60 seconds to wake up after sleeping

---

## Quick Reference

- **Repository**: https://github.com/ebtenorio-myridius/geniushack3
- **Render Dashboard**: https://dashboard.render.com
- **OpenAI Platform**: https://platform.openai.com
- **Health check**: `https://your-app-name.onrender.com/healthz`

---

*This guide is based on the free-first deployment notes already present in the repository (`ops/free-first-deployment.md`) and adapted specifically for Render’s free tier.*
