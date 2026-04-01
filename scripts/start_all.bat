@echo off
echo ========================================
echo PerfHub AI - Starting All Services
echo ========================================
echo.

echo [1/2] Starting Backend...
start "PerfHub Backend" cmd /k "cd backend && python main.py"
timeout /t 3 /nobreak > nul

echo [2/2] Starting Frontend...
start "PerfHub Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo Services started!
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo ========================================
echo.
echo Press any key to stop all services...
pause > nul

taskkill /FI "WindowTitle eq PerfHub Backend*" /T /F
taskkill /FI "WindowTitle eq PerfHub Frontend*" /T /F
