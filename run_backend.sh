#!/bin/bash
echo "Starting TripMind AI Backend on http://localhost:8000..."
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
