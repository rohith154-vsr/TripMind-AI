# TripMind AI 🧭

**Multi-Agent Intelligent Travel Planning Platform**

TripMind AI deploys six specialized AI agents that work concurrently to research destinations, analyze real weather forecasts, discover local restaurants and attractions, manage budgets with live currency conversion, and create a personalized day-by-day itinerary — all synthesized by a central Travel Coordinator Agent.

---

## ✨ Features

- **6 Specialized AI Agents** running concurrently via Python asyncio
- **Real-time Agent Dashboard** with live execution status updates
- **Open-Meteo Integration** — actual weather forecasts, no API key required
- **OpenStreetMap POI Discovery** — real restaurants and attractions via Overpass API
- **Frankfurter Currency Conversion** — live exchange rates, free API
- **Interactive Leaflet Maps** with color-coded POI markers
- **Recharts Visualizations** for weather and budget data
- **SQLite Persistence** for saving and revisiting trip plans
- **Day-by-Day Itinerary** with morning/afternoon/evening breakdown
- **Transparent AI** — agents clearly flag uncertain or unavailable data

---

## 🏗 Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS 3 |
| Icons | Lucide React |
| Charts | Recharts |
| Maps | Leaflet, react-leaflet |
| Backend | Python 3.10+, FastAPI, Uvicorn |
| ORM | SQLAlchemy 2.0 (async) |
| Database | SQLite + aiosqlite |
| AI | Google Gemini API (or OpenAI) |
| HTTP Client | httpx (async) |
| Validation | Pydantic v2 |

---

## 🤖 Agent Architecture

```
User Input
     │
     ▼
Travel Coordinator Agent (orchestrator)
     │
     ├──► Destination Research Agent  → LLM + OSM Nominatim
     ├──► Weather Intelligence Agent  → Open-Meteo + LLM analysis
     ├──► Local Discovery Agent       → OSM Overpass API + LLM enrichment
     ├──► Budget Management Agent     → Frankfurter API + LLM cost analysis
     │
     └──► Itinerary Planning Agent   → LLM (uses all above outputs)
                                           │
                                           ▼
                                   Final Travel Plan (SQLite)
```

### Agent Descriptions

| Agent | External APIs | Responsibility |
|-------|--------------|----------------|
| Destination Research | OSM Nominatim, Gemini | Attractions, activities, cultural tips |
| Weather Intelligence | Open-Meteo, Gemini | Real forecasts, packing tips, schedule adjustments |
| Local Discovery | OSM Overpass API, Gemini | POIs, restaurants, hidden gems |
| Budget Management | Frankfurter API, Gemini | Cost breakdown, currency conversion, savings tips |
| Itinerary Planning | Gemini | Day-by-day schedule using all agent outputs |
| Travel Coordinator | Gemini | Orchestrates all agents, synthesizes final plan |

---

## 🔌 External API Integrations

| API | Purpose | Requires Key? |
|-----|---------|---------------|
| Google Gemini API | AI reasoning for all agents | ✅ Yes |
| Open-Meteo | Weather forecasts | ❌ Free |
| OSM Nominatim | Geocoding / coordinates | ❌ Free |
| OSM Overpass API | Points of interest | ❌ Free |
| Frankfurter API | Currency exchange rates | ❌ Free |
| Leaflet / OSM Tiles | Interactive maps | ❌ Free |

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### Backend Setup

```bash
cd backend

# Copy and edit environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Install Python dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## ⚙ Environment Variables

Edit `backend/.env`:

```env
AI_PROVIDER=gemini           # "gemini" or "openai"
GEMINI_API_KEY=your_key      # From https://aistudio.google.com/apikey
OPENAI_API_KEY=              # Only if AI_PROVIDER=openai
GEMINI_MODEL=gemini-1.5-flash
DATABASE_URL=sqlite+aiosqlite:///./tripmind.db
CORS_ORIGINS=http://localhost:5173
LLM_TIMEOUT=90
HTTP_TIMEOUT=30
```

---

## 📁 Project Structure

```
TripMind-AI/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app
│   │   ├── config.py             # Settings
│   │   ├── database.py           # Async SQLAlchemy
│   │   ├── agents/
│   │   │   ├── coordinator.py    # Orchestrator
│   │   │   ├── destination_agent.py
│   │   │   ├── weather_agent.py
│   │   │   ├── local_discovery_agent.py
│   │   │   ├── budget_agent.py
│   │   │   └── itinerary_agent.py
│   │   ├── services/
│   │   │   ├── llm_service.py    # Gemini/OpenAI abstraction
│   │   │   ├── weather_service.py # Open-Meteo
│   │   │   ├── maps_service.py   # OSM Nominatim + Overpass
│   │   │   └── currency_service.py # Frankfurter
│   │   ├── models/trip.py        # SQLAlchemy ORM
│   │   ├── schemas/trip_schema.py # Pydantic
│   │   └── api/
│   │       ├── trip_routes.py
│   │       └── agent_routes.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── LandingPage.jsx
    │   │   ├── TripPlannerPage.jsx
    │   │   ├── AgentDashboardPage.jsx
    │   │   ├── ResultsDashboardPage.jsx
    │   │   └── SavedTripsPage.jsx
    │   ├── components/
    │   │   ├── Navbar.jsx
    │   │   ├── AgentCard.jsx
    │   │   ├── TripMap.jsx
    │   │   └── Charts.jsx
    │   └── services/api.js
    └── vite.config.js
```

---

## 🔗 API Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| POST | `/api/trips/generate` | Generate new travel plan |
| GET | `/api/trips` | List all saved trips |
| GET | `/api/trips/{id}` | Get a specific trip |
| DELETE | `/api/trips/{id}` | Delete a trip |
| GET | `/api/agents/status/{id}` | Poll agent execution status |
| GET | `/api/agents/stream/{id}` | SSE stream of agent updates |
| GET | `/api/health` | Backend health check |

Interactive API docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📸 Screenshots

> Add screenshots of the Landing Page, Trip Planner, Agent Dashboard, and Results Dashboard here.

---

## 🔒 Security Notes

- API keys stored in `.env` (gitignored)
- CORS restricted to configured origins
- Input validation via Pydantic v2
- No credentials exposed in frontend code
- Request timeouts on all external API calls

---

## 📄 License

MIT License — Built as a portfolio project demonstrating multi-agent AI architecture.
