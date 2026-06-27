@echo off
title BHA Platform — Push to GitHub
cd /d "%~dp0"

echo.
echo  Initializing git and pushing to GitHub...
echo.

git init
git branch -M main
git add .
git commit -m "BHA Platform v2.0 — initial deploy"
git remote add origin https://github.com/Agentic-Auditor/bha-platform.git
git push -u origin main

echo.
echo  Done! Code pushed to GitHub.
echo  https://github.com/Agentic-Auditor/bha-platform
echo.
pause
