# TripMind AI 🧭

<p align="center">
  <strong>Your personal travel-planning team, powered by collaborating AI agents.</strong>
  <br />
  Research destinations, understand the weather, estimate costs and build a day-by-day itinerary in one place.
</p>

<p align="center">
  <a href="https://github.com/rohith154-vsr/TripMind-AI"><img src="https://img.shields.io/badge/status-active%20development-brightgreen" alt="Project status" /></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/AI-Google%20Gemini-8E75B2?logo=googlegemini&logoColor=white" alt="Google Gemini" />
  <img src="https://img.shields.io/badge/tests-18%20passing-success" alt="18 tests passing" />
</p>

---

## Overview

**TripMind AI** is a multi-agent travel-planning application built with React, FastAPI and Google Gemini. A central Travel Coordinator orchestrates specialized agents that research a destination, retrieve weather information, discover nearby points of interest, estimate expenses and prepare a day-wise itinerary.

The application is designed around **transparent, evidence-aware recommendations**: agent outputs identify whether information came from an LLM, a live external API, a hybrid process or a fallback. If a live place-discovery service is unavailable, TripMind AI does not invent venue names or coordinates.

> **Project status:** The application has been run and verified locally. The latest verification recorded 18 passing backend tests and a successful Vite production build. External public services can impose rate limits or experience outages; the application labels fallback or unavailable data rather than treating it as live.

## Key Features

- **Multi-agent orchestration** — six specialized agents coordinate through a central Travel Coordinator.
- **Destination research** — destination highlights, activities and practical travel context.
- **Weather intelligence** — forecast retrieval through Open-Meteo, with weather-aware suggestions.
- **Local discovery** — geographical points of interest through OpenStreetMap services when available.
- **Budget planning** — category-wise expense estimates and currency conversion with rate provenance.
- **Day-wise itinerary** — morning, afternoon and evening plans with geographic grouping.
- **Agent transparency dashboard** — execution state, responsibility, source type, data sources, duration and errors.
- **Interactive map** — Leaflet map with markers for available, geocoded places.
- **Visual summaries** — Recharts charts for budget and weather information.
- **Saved trips** — SQLite persistence for generated plans.
- **Graceful fallback behavior** — useful offline/domain fallback behavior when optional AI or public API services cannot be reached.
- **No fabricated establishments** — unavailable live POI results are shown as unavailable; synthetic venue names, addresses and coordinates are not presented as real.

## How the Multi-Agent Workflow Works

The user submits a destination, dates, group size, budget, travel style and interests. The coordinator then runs the independent research tasks, gathers their results and requests itinerary planning and final synthesis.

~~~mermaid
flowchart TD
    U[User trip preferences] --> C[Travel Coordinator]
    C --> D[Destination Research Agent]
    C --> W[Weather Intelligence Agent]
    C --> L[Local Discovery Agent]
    C --> B[Budget Management Agent]
    D --> I[Itinerary Planning Agent]
    W --> I
    L --> I
    B --> I
    I --> C2[Coordinator synthesis]
    C2 --> R[Final travel plan]
    R --> DB[(SQLite trip storage)]
    R --> UI[Results dashboard]
~~~

### The Six Agents

| Agent | Main responsibility | Data and services |
|---|---|---|
| Destination Research | Destination context, attractions, activities and practical tips | Gemini; Nominatim geocoding |
| Weather Intelligence | Forecast interpretation, weather-aware advice and packing suggestions | Open-Meteo; optional LLM analysis |
| Local Discovery | Nearby POIs and local recommendations | OpenStreetMap Overpass; fallback guidance when live discovery is unavailable |
| Budget Management | Expense categories, budget feasibility and conversion | Frankfurter exchange rates; calculation logic; optional LLM analysis |
| Itinerary Planning | Day-wise schedule, activity grouping and itinerary consistency | Gemini and outputs from the other agents |
| Travel Coordinator | Orchestration, progress tracking and final synthesis | Gemini and agent outputs |

### Agent Result Provenance

Agent results include metadata intended to distinguish the generation path:

- **llm** — generated using the configured language model.
- **live_api** — retrieved from an external live data service.
- **hybrid** — combines external data and model reasoning.
- **fallback** — generated through local fallback logic when a live dependency is unavailable.

A successful agent execution does not necessarily mean every external provider was available. Check the provenance labels and notices shown in the application.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React 19, Vite 8, Tailwind CSS |
| Routing and HTTP | React Router, Axios |
| UI and icons | Lucide React |
| Charts | Recharts |
| Maps | Leaflet, React Leaflet, OpenStreetMap |
| Backend | Python, FastAPI, Uvicorn |
| Data validation | Pydantic v2, pydantic-settings |
| Persistence | SQLAlchemy 2 async, SQLite, aiosqlite |
| AI providers | Google Gemini; OpenAI provider option |
| HTTP clients | httpx |
| Tests | pytest, pytest-asyncio, HTTPX |

## External API Integrations

| Service | Purpose | Credential |
|---|---|---|
| Google Gemini API | LLM reasoning and synthesis | API key required |
| OpenAI API | Alternative LLM provider | API key required if selected |
| Open-Meteo | Weather forecasts | No API key for the configured public endpoint |
| OpenStreetMap Nominatim | Geocoding and coordinates | No API key; usage policy and request limits apply |
| OpenStreetMap Overpass | Nearby points of interest | No API key; public instances may rate-limit or time out |
| Frankfurter | Currency exchange rates | No API key for the configured public endpoint |
| OpenStreetMap tiles / Leaflet | Map display | No application API key for the configured setup |

**Live-service caveat:** Public endpoints are third-party dependencies, not guaranteed infrastructure. Overpass availability can vary by region and load. When place discovery returns no verified records, TripMind AI should show no fabricated venues and provide a clear unavailable-data notice. Currency fallback values, where used, must remain explicitly labelled as estimates rather than live rates.

## Application Pages

| Page | Route | Purpose |
|---|---|---|
| Landing | **/** | Product introduction and entry point |
| Trip Planner | **/plan** | Enter trip details and preferences |
| Agent Dashboard | **/agents/:id** | Follow agent execution and provenance |
| Results Dashboard | **/results/:id** | Review itinerary, map, weather and budget |
| Saved Trips | **/saved** | Reopen or delete saved trip plans |

## Quickstart

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- A Google Gemini API key for live Gemini-powered reasoning (optional fallback behavior is available without it)

### Option A: One-command launch

From the repository root:

**Windows**
~~~bat
run_all.bat
~~~

**macOS / Linux**
~~~bash
chmod +x run_all.sh
./run_all.sh
~~~

The launcher scripts start the backend and frontend in separate processes. If a launcher does not work in your environment, use the manual setup below.

### Option B: Manual setup

#### 1. Clone the repository

~~~bash
git clone https://github.com/rohith154-vsr/TripMind-AI.git
cd TripMind-AI
~~~

#### 2. Configure the backend

**Windows PowerShell**
~~~powershell
cd backend
Copy-Item .env.example .env
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
~~~

**macOS / Linux**
~~~bash
cd backend
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
~~~

Open **backend/.env** and add your Gemini API key. Keep this file local; it is excluded from Git.

Start the backend from the **backend** directory:

~~~bash
uvicorn app.main:app --reload --port 8000
~~~

Backend health check: [http://localhost:8000/api/health](http://localhost:8000/api/health)  
Interactive API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

#### 3. Configure and start the frontend

Open a second terminal at the repository root:

~~~bash
cd frontend
npm install
npm run dev
~~~

Open [http://localhost:5173](http://localhost:5173).

## Environment Configuration

The backend reads configuration from **backend/.env**. The tracked **backend/.env.example** contains placeholders only.

Common settings:

| Variable | Description |
|---|---|
| AI_PROVIDER | Select gemini or openai |
| GEMINI_API_KEY | Google AI Studio API key |
| OPENAI_API_KEY | OpenAI API key when using OpenAI |
| GEMINI_MODEL | Gemini model identifier |
| OPENAI_MODEL | OpenAI model identifier |
| DATABASE_URL | SQLAlchemy database connection string |
| CORS_ORIGINS | Comma-separated allowed frontend origins |
| LLM_TIMEOUT | LLM request timeout in seconds |
| HTTP_TIMEOUT | External HTTP request timeout in seconds |

Example local configuration:

~~~env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite+aiosqlite:///./tripmind.db
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LLM_TIMEOUT=90
HTTP_TIMEOUT=30
~~~

Use model identifiers supported by your provider account and current provider documentation. Never put API keys in frontend environment variables, source code, screenshots or commits.

## Running Tests and Building

Backend tests:

~~~bash
cd backend
python -m pytest tests -v
~~~

Frontend production build:

~~~bash
cd frontend
npm run build
~~~

The latest project verification report recorded **18 passing backend tests** and a successful frontend production build. Run the commands above against your local environment to verify the current checkout and dependency versions.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/trips/generate | Generate a trip plan |
| GET | /api/trips | List saved trips |
| GET | /api/trips/{id} | Retrieve a saved trip |
| DELETE | /api/trips/{id} | Delete a saved trip |
| GET | /api/agents/status/{id} | Retrieve agent execution status |
| GET | /api/agents/stream/{id} | Stream agent updates using SSE |
| GET | /api/health | Check backend health |

Interactive endpoint documentation is available at **/docs** when the backend is running.

## Repository Structure

~~~text
TripMind-AI/
├── backend/
│   ├── app/
│   │   ├── agents/          # Coordinator and specialized agents
│   │   ├── api/             # FastAPI route handlers
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # LLM, weather, maps, currency, fallback
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── tests/               # Agent, service, API and integrity tests
│   ├── requirements.txt
│   └── .env.example
├── docs/
│   ├── ARCHITECTURE.md
│   └── screenshots/
│       ├── 01-landing-page.png
│       ├── 02-trip-planner.png
│       ├── 03-agent-dashboard.png
│       ├── 04-results-dashboard.png
│       └── 05-saved-trips.png
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   └── package.json
├── run_all.bat
├── run_all.sh
├── run_backend.bat
├── run_backend.sh
├── run_frontend.bat
├── run_frontend.sh
└── README.md
~~~

For a more detailed system view, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Screenshots

Visual walkthrough of TripMind AI captured directly from the running application:

### 1. Landing Page
*Modern, responsive landing interface introducing the multi-agent travel planning platform.*

![TripMind AI Landing Page](docs/screenshots/01-landing-page.png)

### 2. Trip Planning Form
*Input form capturing trip parameters including destination, dates, budget, currency, and travel preferences.*

![Trip Planning Form](docs/screenshots/02-trip-planner.png)

### 3. Agent Execution Dashboard (Live Provenance & Metrics)
*Real-time orchestrator tracking all 6 specialized agents, displaying execution status, duration, data sources, and transparent provenance badges (AI Reasoning, Live External API, Hybrid, and Fallback).*

![Agent Execution Dashboard](docs/screenshots/03-agent-dashboard.png)

### 4. Comprehensive Results Dashboard
*Synthesized travel plan featuring Day-by-Day Itinerary, Budget Breakdown (with Recharts visualization & live Frankfurter exchange rate), Weather Forecast (with Recharts chart), Regional Dining Guide, and Leaflet Interactive Map.*

![Results Dashboard](docs/screenshots/04-results-dashboard.png)

### 5. Saved Trips
*Persistent trip history backed by async SQLite, allowing users to revisit, inspect, or manage previously generated travel plans.*

![Saved Trips Page](docs/screenshots/05-saved-trips.png)

## Security

- Keep provider credentials in the local **backend/.env** file.
- Do not commit .env files, API keys, tokens or local database files.
- The repository includes an environment template with placeholder values.
- Validate inputs on the backend and configure CORS for the deployment environment.
- External API calls use configured timeouts and may fail or be rate-limited.
- Rotate any credential immediately if it is accidentally exposed.

## License

No license file is currently included in this repository. Unless a license is added, the source remains subject to the default copyright rules; do not assume it is MIT-licensed.

---

<p align="center">
  Built to explore practical multi-agent AI orchestration, API integration and transparent AI-assisted travel planning.
</p>
