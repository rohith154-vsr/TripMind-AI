#!/bin/bash
echo "Starting TripMind AI (Backend + Frontend)..."
(cd backend && python -m uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!
(cd frontend && npm run dev) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
echo "Backend running on http://localhost:8000 (PID $BACKEND_PID)"
echo "Frontend running on http://localhost:5173 (PID $FRONTEND_PID)"
wait

