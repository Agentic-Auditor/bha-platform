@echo off
title BHA Deploy
cd /d "%~dp0"
(
echo CWD=%cd%
echo --- clearing stale git locks ---
del /f /q /s ".git\*.lock" 2>nul
git --version
echo --- init ---
git init
git branch -M main
git config user.email "agenticauditor24@gmail.com"
git config user.name "Agentic Auditor"
echo --- add ---
git add -A
echo --- commit ---
git commit -m "deploy: BHA backend update (golden, phase-2, strict validation, KPI start-date, observability, AA branding/logo, CI)"
echo --- remote ---
git remote remove origin
git remote add origin https://github.com/Agentic-Auditor/bha-platform.git
echo --- push force ---
git push -u origin main --force
echo --- EXIT %errorlevel% ---
) > _deploy_out.txt 2>&1
type _deploy_out.txt | clip
type _deploy_out.txt
echo.
echo (Output copied to clipboard.)
pause
