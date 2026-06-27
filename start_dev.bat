@echo off
title BHA Platform — Dev Server
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   BHA Platform — Starting Dev Mode  ║
echo  ╚══════════════════════════════════════╝
echo.

REM ── Check .env exists, else create default
if not exist ".env" (
    echo SECRET_KEY=dev-secret-key-change-me-in-prod > .env
    echo ADMIN_TOKEN=admin123 >> .env
    echo ANTHROPIC_API_KEY= >> .env
    echo FRONTEND_URL=http://localhost:3000 >> .env
    echo [INFO] Created default .env file
)

REM ── Load .env
for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b

REM ── Start Flask backend in new window
echo [1/2] Starting Flask backend on http://localhost:5000 ...
start "BHA Backend (Flask)" cmd /k "cd /d %~dp0 && python app.py"

REM ── Wait 2s then start Next.js
timeout /t 2 /nobreak >nul

echo [2/2] Starting Next.js frontend on http://localhost:3000 ...
start "BHA Frontend (Next.js)" cmd /k "cd /d %~dp0frontend && npm run dev"

REM ── Wait then open browser
timeout /t 5 /nobreak >nul
echo.
echo  Opening http://localhost:3000 ...
start "" "http://localhost:3000"

echo.
echo  [DONE] Both servers running. Close the two terminal windows to stop.
pause
