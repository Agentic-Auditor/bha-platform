@echo off
title BHA Platform — Push Membership System v3
cd /d "%~dp0"

echo.
echo  ======================================================
echo   BHA Platform — Membership System Push
echo  ======================================================
echo.

:: Check git
git --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: git not found. Install Git for Windows first.
    pause
    exit /b 1
)

:: Re-init and push (same pattern as before)
git init
git branch -M main

git add app.py
git add schema.sql
git add frontend/lib/api.js
git add frontend/app/login/page.js
git add frontend/app/member/page.js
git add frontend/app/membership/payment/page.js

git status --short

echo.
set /p CONFIRM="Push these files? (y/n): "
if /i "%CONFIRM%" neq "y" (
    echo Cancelled.
    pause
    exit /b 0
)

git commit -m "feat: Membership System v3 — email auth, trend dashboard, alert system, PromptPay 890 THB"

:: Add remote only if not already set
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    git remote add origin https://github.com/Agentic-Auditor/bha-platform.git
)

git push -u origin main --force

echo.
echo  Done! Railway will auto-deploy in ~2 minutes.
echo  https://bha-platform-production.up.railway.app/api/health
echo.
pause
