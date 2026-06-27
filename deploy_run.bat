@echo off
title BHA Deploy
cd /d "%~dp0"
(
del /f /q /s ".git\*.lock" 2>nul
git add -A
git commit -m "fix: rebrand dashboard CTA to Agentic-Auditor + link to www.agentic-auditor.com"
git push origin main
echo --- EXIT %errorlevel% ---
) > _deploy_out.txt 2>&1
type _deploy_out.txt | clip
echo done
pause
