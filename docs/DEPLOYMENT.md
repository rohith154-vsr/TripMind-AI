# TripMind AI — Production Deployment Guide

This guide describes how to deploy TripMind AI into production using:

- **Database:** Neon (Serverless PostgreSQL)
- **Backend:** Render (FastAPI Web Service)
- **Frontend:** Vercel (React 18 + Vite SPA)

---

## Architecture Overview

```
                      ┌─────────────────────────────────┐
                      │          Web Browser            │
                      └────────────────┬────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      │   Vercel CDN (React Frontend)   │
                      │   https://your-app.vercel.app   │
                      └────────────────┬────────────────┘
                                       │ HTTPS (CORS)
                                       ▼
                      ┌─────────────────────────────────┐
                      │    Render (FastAPI Backend)     │
                      │ https://your-service.onrender.com │
                      └───────┬───────────────────┬─────┘
                              │                   │
             Async Engine     │                   │ HTTPS
             (asyncpg + SSL)  │                   │
                              ▼                   ▼
                      ┌───────────────┐   ┌───────────────────────────┐
                      │ Neon Database │   │ External APIs:            │
                      │ (PostgreSQL)  │   │ • Google Gemini           │
                      └───────────────┘   │ • Open-Meteo              │
                                          │ • OpenStreetMap           │
                                          │ • Frankfurter             │
                                          └───────────────────────────┘
```

---

## 1. Database Setup: Neon PostgreSQL

1. Sign up or log in at [Neon Console](https://console.neon.tech).
2. Click **Create Project**.
   - **Project Name:** `tripmind-ai`
   - **Region:** Choose a region geographically close to your Render deployment (e.g., `us-east-2` or `eu-central-1`).
3. After creation, copy the **Connection string** from the project dashboard.
   - You can choose either **Direct** or **Pooled connection** (PgBouncer):
     ```
     postgresql://alex:AbC123dEf@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
     ```
4. **Note on compatibility:** TripMind AI's `backend/app/database.py` automatically:
   - Detects and translates `postgresql://` into `postgresql+asyncpg://`.
   - Maps `sslmode=require` into `ssl=require`, preserving TLS security.
   - Strips unsupported libpq query parameters like `channel_binding=require`.
   - Disables statement caching (`statement_cache_size=0`) when a pooled host (`-pooler`) is used, preventing PgBouncer transaction-mode prepared statement conflicts.
   You do not need to manually modify or clean the connection string.

---

## 2. Backend Deployment: Render

1. Log in to [Render](https://dashboard.render.com).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository: `rohith154-vsr/TripMind-AI`.
4. Configure the service settings:
   - **Name:** `tripmind-ai-backend` (or your preferred name)
   - **Region:** Same region as your Neon database if possible
   - **Branch:** `master`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type:** Free (or Starter for continuous uptime)

5. Under **Advanced**, set **Health Check Path** to:
   ```
   /api/health
   ```

6. Add the following **Environment Variables** in the Render Dashboard:

| Variable | Recommended Value | Description |
|---|---|---|
| `APP_ENV` | `production` | Sets application mode |
| `DATABASE_URL` | `postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require` | Neon connection string |
| `AI_PROVIDER` | `gemini` | Primary AI provider |
| `GEMINI_API_KEY` | `AIzaSy...` | Your Google AI Studio API key |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Supported fast model |
| `CORS_ORIGINS` | `https://your-frontend.vercel.app` | Vercel production URL (add temporary `http://localhost:5173` until Vercel is ready) |
| `CORS_ORIGIN_REGEX` | `https://.*\.vercel\.app` | *(Optional)* Allows Vercel preview branch deployments |
| `LLM_TIMEOUT` | `90` | Seconds before LLM times out |
| `HTTP_TIMEOUT` | `30` | Seconds for external APIs (Overpass, Weather) |

7. Click **Deploy Web Service**.
8. Once deployment finishes, copy your Render service URL:
   `https://tripmind-ai-backend.onrender.com`

---

## 3. Frontend Deployment: Vercel

1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** > **Project** and import `rohith154-vsr/TripMind-AI`.
3. Configure project settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** Click Edit and select `frontend`
   - **Build Command:** `npm run build` (detected automatically)
   - **Output Directory:** `dist` (detected automatically)
   - **Install Command:** `npm install` (detected automatically)

4. In **Environment Variables**, add:

| Key | Value | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `https://tripmind-ai-backend.onrender.com` | Your deployed Render backend URL |

> **Important:** Do not add a trailing slash to `VITE_API_BASE_URL`. Do not expose any backend secret keys in frontend environment variables.

5. Click **Deploy**.
6. When deployment finishes, copy your Vercel deployment URL:
   `https://tripmind-ai.vercel.app`

---

## 4. Connecting Frontend and Backend

To complete the connection:

1. Return to the **Render Dashboard** > `tripmind-ai-backend` > **Environment**.
2. Update `CORS_ORIGINS` to include your production Vercel URL:
   ```
   CORS_ORIGINS=https://tripmind-ai.vercel.app,http://localhost:5173
   ```
3. Save changes. Render will automatically redeploy with the updated CORS policy.

---

## 5. Deployment Verification Checklist

Verify the deployed components in this sequence:

1. **Backend Health Check:**
   ```bash
   curl https://tripmind-ai-backend.onrender.com/api/health
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "service": "TripMind AI Backend",
     "version": "1.0.0",
     "ai_provider": "gemini"
   }
   ```

2. **Database Initialization:**
   - On initial startup, FastAPI's lifespan event runs `init_db()`.
   - In Neon Console, check the **Tables** tab under `neondb` to verify that the `trips` table was created.

3. **Interactive API Documentation:**
   - Visit `https://tripmind-ai-backend.onrender.com/docs` to inspect OpenAPI endpoints.

4. **Frontend Navigation & Direct Linking:**
   - Visit `https://tripmind-ai.vercel.app/`
   - Navigate to `/plan`
   - Directly refresh `https://tripmind-ai.vercel.app/saved` to confirm `vercel.json` SPA rewrites function without 404s.

5. **End-to-End Trip Generation:**
   - Submit a test plan on the trip planner form.
   - Verify that the Agent Execution Dashboard connects to the Render backend, displays live agent progress, and stores the completed travel plan in Neon.

---

## 6. Troubleshooting & Common Issues

### 1. Render Free Tier Cold Starts
- **Symptom:** The first request to the frontend or `/api/health` takes 45–60 seconds to respond.
- **Cause:** Render spins down free tier web services after 15 minutes of inactivity.
- **Remedy:** Upgrade to Render Starter tier, or use a free monitoring service (e.g. UptimeRobot or Cron-job.org) to ping `/api/health` every 10 minutes.

### 2. CORS Errors in Browser Console
- **Symptom:** `Access to XMLHttpRequest at 'https://...onrender.com/api/...' from origin 'https://...vercel.app' has been blocked by CORS policy`.
- **Cause:** `CORS_ORIGINS` on Render does not contain the exact Vercel URL (or has an extra trailing slash).
- **Remedy:** Ensure `CORS_ORIGINS` on Render matches your Vercel URL exactly without a trailing slash (e.g. `https://tripmind-ai.vercel.app`).

### 3. Server-Sent Events (SSE) Stream Dropping
- **Symptom:** EventSource fails to connect or closes prematurely.
- **Cause:** Proxy buffering or mismatched protocol.
- **Remedy:** TripMind AI frontend automatically falls back to polling `/api/agents/status/{id}` every 2 seconds if the SSE connection drops, ensuring uninterrupted progress tracking.

### 4. Neon Serverless Connection Drops
- **Symptom:** `asyncpg.exceptions.ConnectionDoesNotExistError` or closed connection after periods of inactivity.
- **Cause:** Neon serverless compute suspends after 5 minutes of idle time.
- **Remedy:** The application engine is configured with `pool_pre_ping=True` and `pool_recycle=300`. This verifies database connectivity before executing queries and transparently reconnects when Neon compute awakens.

### 5. PostgreSQL `sslmode` Error
- **Symptom:** `TypeError: connect() got an unexpected keyword argument 'sslmode'`.
- **Cause:** `asyncpg` uses the `ssl` argument instead of `sslmode`.
- **Remedy:** TripMind AI's `format_database_url` function intercepts `sslmode=require` and maps it to `ssl=require`, ensuring full compatibility with Neon connection strings.

