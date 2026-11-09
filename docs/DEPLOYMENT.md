# TripMind AI — Production Deployment Guide

This guide describes how to deploy TripMind AI to production using:

- **Database:** Neon (Serverless PostgreSQL with SSL)
- **Backend:** Render (FastAPI Web Service with Async SQLAlchemy & asyncpg)
- **Frontend:** Vercel (React 19 + Vite SPA)

---

## Production Architecture Overview

```
                      ┌─────────────────────────────────┐
                      │          Web Browser            │
                      └────────────────┬────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      │   Vercel CDN (React 19 SPA)     │
                      │ https://trip-mind-ai-vert.vercel.app │
                      └────────────────┬────────────────┘
                                       │ HTTPS (CORS)
                                       ▼
                      ┌─────────────────────────────────┐
                      │    Render (FastAPI Backend)     │
                      │ https://tripmind-ai-backend-a72w.onrender.com │
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
   - **Region:** Choose an AWS region geographically close to your Render deployment (e.g. `us-east-2` or `eu-central-1`).
3. After creation, copy the **Connection string** from the project dashboard.
   - You can choose either **Direct** or **Pooled connection** (PgBouncer):
     ```text
     postgresql://username:password@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
     ```
4. **Compatibility Handling:**
   TripMind AI's `backend/app/database.py` automatically normalizes connection strings:
   - Detects and converts `postgresql://` and `postgres://` into `postgresql+asyncpg://`.
   - Maps `sslmode=require` to `ssl=require`, ensuring asyncpg connects securely via TLS.
   - Strips unsupported libpq query parameters such as `channel_binding=require`.
   - When connecting via Neon's connection pooler (`-pooler` in hostname), automatically sets `statement_cache_size=0` to prevent PgBouncer transaction-mode prepared statement collisions.
   - Configures connection pooling with `pool_pre_ping=True` and `pool_recycle=300` to transparently handle Neon compute wake-ups.

---

## 2. Backend Deployment: Render

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository: `rohith154-vsr/TripMind-AI`.
4. Configure service settings:
   - **Name:** `tripmind-ai-backend` (service name in Render dashboard)
   - **Region:** Same region as your Neon database (e.g. `Ohio (US East)`)
   - **Branch:** `master`
   - **Root Directory:** `backend` *(Critical: must be `backend`, not repository root)*
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
   ```text
   /api/health
   ```

6. Add the following **Environment Variables** in the Render Dashboard:

| Variable | Recommended Value | Description |
|---|---|---|
| `APP_ENV` | `production` | Enforces production settings |
| `DATABASE_URL` | `postgresql://user:password@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require` | Neon connection string with SSL |
| `AI_PROVIDER` | `gemini` | Primary AI provider |
| `GEMINI_API_KEY` | `AIzaSy...` | Your Google AI Studio API key |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Recommended fast, high-quality model |
| `CORS_ORIGINS` | `https://trip-mind-ai-vert.vercel.app` | Exact production Vercel frontend URL (no trailing slash) |
| `CORS_ORIGIN_REGEX` | *(Leave empty)* | Optional; only use if preview branch deployments are required |
| `LLM_TIMEOUT` | `90` | Seconds before LLM request times out |
| `HTTP_TIMEOUT` | `30` | Seconds before external API calls time out |

7. Click **Deploy Web Service**.
8. Once deployment finishes, copy your live public backend URL (Render assigns a generated hostname for free tier services, e.g. `https://tripmind-ai-backend-a72w.onrender.com`):
   `https://tripmind-ai-backend-a72w.onrender.com`

---

## 3. Frontend Deployment: Vercel

1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** > **Project** and import `rohith154-vsr/TripMind-AI`.
3. Configure the project settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** Click Edit and select `frontend`
   - **Build Command:** `npm run build` (detected automatically)
   - **Output Directory:** `dist` (detected automatically)
   - **Install Command:** `npm install` (detected automatically)

4. In **Environment Variables**, add:

| Key | Value | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `https://tripmind-ai-backend-a72w.onrender.com` | Deployed Render backend URL (no trailing slash) |

> **Important:** Do not add a trailing slash to `VITE_API_BASE_URL`. Never expose backend API keys or database credentials in frontend environment variables.

5. Click **Deploy**.
6. When deployment finishes, your Vercel frontend is live at:
   `https://trip-mind-ai-vert.vercel.app`

---

## 4. Connecting Frontend and Backend (CORS Configuration)

To ensure secure cross-origin communication:

1. In the **Render Dashboard**, go to your backend web service (`tripmind-ai-backend`) > **Environment**.
2. Verify that `CORS_ORIGINS` contains your exact Vercel production domain:
   ```text
   CORS_ORIGINS=https://trip-mind-ai-vert.vercel.app
   ```
   *(If testing locally against the cloud backend, you can append `,http://localhost:5173`)*
3. **CORS Isolation Rule:** Do not use wildcard regex patterns (such as `https://.*\.vercel\.app`) in production, as this would allow any Vercel deployment across the entire platform to access your backend API.
4. Save any changes. Render will automatically redeploy with the updated CORS policy.

---

## 5. Deployment Verification Checklist

Verify the deployed production components in this sequence:

1. **Backend Health Check:**
   ```bash
   curl https://tripmind-ai-backend-a72w.onrender.com/api/health
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

2. **Database Connectivity Smoke Test:**
   ```bash
   curl https://tripmind-ai-backend-a72w.onrender.com/api/health/db
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "database": "connected"
   }
   ```
   *Note:* If database credentials or networking fail, this endpoint returns HTTP 503 (`{"status": "unhealthy", "database": "disconnected"}`) without leaking internal exception, host, or credential details.

3. **Database Initialization Verification:**
   - On initial startup, FastAPI's lifespan event executes `init_db()`.
   - In Neon Console, navigate to the **Tables** tab under `neondb` to verify that both `trips` and `agent_statuses` tables have been created.

4. **Interactive API Documentation:**
   - Open `https://tripmind-ai-backend-a72w.onrender.com/docs` in your browser to inspect the registered OpenAPI routes.

5. **Frontend Navigation & Direct Linking:**
   - Visit `https://trip-mind-ai-vert.vercel.app/`
   - Navigate to `/plan`
   - Refresh directly on `https://trip-mind-ai-vert.vercel.app/saved` to confirm `vercel.json` SPA rewrite rules function without 404 errors.

6. **End-to-End Trip Generation:**
   - Submit a test plan on the trip planner form.
   - Verify that the Agent Execution Dashboard connects to the Render backend, displays live agent progress, and stores the completed travel plan in Neon.

---

## 6. Operational Considerations & Troubleshooting

### 1. Render Free Tier Cold Starts
- **Symptom:** The initial request to the backend or `/api/health` takes 45–60 seconds to respond.
- **Cause:** Render spins down free tier web services after 15 minutes of inactivity.
- **Remedy:** This is expected behavior on Render's free tier. Once spun up, subsequent requests respond immediately. For persistent zero-delay uptime in production environments, upgrade to Render's Starter instance tier.

### 2. CORS Errors in Browser Console
- **Symptom:** `Access to XMLHttpRequest at 'https://...onrender.com/api/...' from origin 'https://...vercel.app' has been blocked by CORS policy`.
- **Cause:** `CORS_ORIGINS` on Render does not contain the exact Vercel URL, or contains an accidental trailing slash.
- **Remedy:** Verify that `CORS_ORIGINS` on Render is set to `https://trip-mind-ai-vert.vercel.app` (without trailing slashes or unneeded spaces).

### 3. Server-Sent Events (SSE) Stream Handling
- **Symptom:** EventSource connection closes prematurely during long agent pipelines.
- **Remedy:** The TripMind AI frontend includes an automatic polling fallback: if the SSE connection drops, it smoothly falls back to polling `/api/agents/status/{id}` every 2 seconds until all agents complete.

### 4. Neon Serverless Compute Suspension
- **Symptom:** Initial database query after a period of inactivity takes 1–3 seconds longer.
- **Cause:** Neon serverless compute branches suspend when idle to conserve resources.
- **Remedy:** The backend engine is configured with `pool_pre_ping=True` and `pool_recycle=300`. It automatically validates connections and re-establishes connectivity as soon as Neon compute awakens.

### 5. PostgreSQL Dialect & SSL Parameter Handling
- **Symptom:** `TypeError: connect() got an unexpected keyword argument 'sslmode'`.
- **Cause:** `asyncpg` requires the `ssl` argument rather than `sslmode`.
- **Remedy:** TripMind AI's `format_database_url` function automatically translates `sslmode=require` to `ssl=require` and strips unsupported parameters (`channel_binding`), ensuring full out-of-the-box compatibility with Neon connection strings.
