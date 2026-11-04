@echo off
echo ========================================================
echo Starting TripMind AI (Backend + Frontend)
echo ========================================================
start "TripMind AI Backend" cmd /k "cd backend && python -m uvicorn app.main:app --reload --port 8000"
start "TripMind AI Frontend" cmd /k "cd frontend && npm run dev"
echo Backend running on http://localhost:8000
echo Frontend running on http://localhost:5173
echo Press any key to exit this launcher window...
pause >nul

