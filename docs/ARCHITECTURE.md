# TripMind AI — System Architecture

This document describes the current high-level architecture of TripMind AI.

## 1. System Context

~~~mermaid
flowchart LR
    Traveller[Traveller] --> Web[React Web Application]
    Web --> API[FastAPI Backend]
    API --> Orchestrator[Travel Coordinator]
    Orchestrator --> Agents[Specialized Agent Layer]
    Agents --> Providers[External Data and LLM Providers]
    Agents --> Store[(SQLite)]
    Orchestrator --> Store
    API --> Web
~~~

## 2. Agent Collaboration

~~~mermaid
flowchart TD
    Request[Validated Trip Request] --> Coordinator[Travel Coordinator]
    Coordinator --> Destination[Destination Research]
    Coordinator --> Weather[Weather Intelligence]
    Coordinator --> Discovery[Local Discovery]
    Coordinator --> Budget[Budget Management]
    Destination --> Itinerary[Itinerary Planning]
    Weather --> Itinerary
    Discovery --> Itinerary
    Budget --> Itinerary
    Itinerary --> Synthesis[Coordinator Synthesis]
    Synthesis --> Persist[Persist Trip Result]
    Persist --> Response[Results Dashboard]
~~~

The coordinator owns the workflow. Independent research tasks can run concurrently. Itinerary planning uses the collected research and planning outputs, and the coordinator synthesizes the completed result.

## 3. Agent Responsibilities and Data Sources

| Agent | Responsibility | Primary dependencies |
|---|---|---|
| Destination Research | Destination context, attractions and practical tips | Gemini; Nominatim |
| Weather Intelligence | Forecast interpretation and weather-aware advice | Open-Meteo; optional LLM reasoning |
| Local Discovery | Verified nearby places and regional guidance | Overpass; Nominatim; fallback behavior |
| Budget Management | Expense allocation, feasibility and currency conversion | Frankfurter; calculation logic |
| Itinerary Planning | Date-aware, geographically grouped daily schedule | Gemini and upstream agent outputs |
| Travel Coordinator | Orchestration, progress and final synthesis | Agent outputs; configured LLM |

## 4. Provenance Model

Agent metadata communicates how an output was produced:

| Source type | Meaning |
|---|---|
| llm | Language-model-generated output |
| live_api | Data retrieved from a live external API |
| hybrid | Live external data combined with LLM reasoning |
| fallback | Local fallback logic used because a dependency was unavailable |

The UI should preserve these distinctions. A completed agent status means its task completed; it does not imply every external provider returned live data.

## 5. External Services

~~~mermaid
flowchart TB
    Backend[FastAPI Services]
    Backend --> Gemini[Google Gemini API]
    Backend --> OpenAI[OpenAI API - optional provider]
    Backend --> Meteo[Open-Meteo Forecast API]
    Backend --> Nominatim[OSM Nominatim Geocoding]
    Backend --> Overpass[OSM Overpass POI Search]
    Backend --> Frankfurter[Frankfurter Exchange Rates]
    Frontend[React + Leaflet] --> Tiles[OpenStreetMap Map Tiles]
~~~

Public geospatial services may impose usage limits or experience congestion. If a place cannot be verified, the application must not invent its name, address or coordinates. Currency fallback values must be clearly marked as estimates.

## 6. Persistence and API Boundary

- FastAPI exposes trip-generation, trip-retrieval, deletion, agent-status and server-sent-event routes.
- SQLAlchemy async models persist trip requests and generated plans in SQLite.
- The frontend communicates with the backend through its API service layer.
- Provider credentials are configured on the backend and must never be exposed to the browser.

## 7. Local Development Ports

| Service | Default URL |
|---|---|
| React + Vite frontend | http://localhost:5173 |
| FastAPI backend | http://localhost:8000 |
| FastAPI interactive docs | http://localhost:8000/docs |
| Backend health endpoint | http://localhost:8000/api/health |
