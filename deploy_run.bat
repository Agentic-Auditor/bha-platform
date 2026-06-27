@echo off
title BHA Deploy
cd /d "%~dp0"
(
del /f /q /s ".git\*.lock" 2>nul
echo --- untrack sandbox junk ---
git rm -r --cached --quiet ".fuse_hidden*" 2>nul
git rm --cached --quiet _deploy_out.txt _deploy_out2.txt _mount_test.txt deploy_run.bat deploy_verify.bat 2>nul
echo --- add ---
git add -A
echo --- commit ---
git commit -m "feat: free-results teasers (hard-floor warnings, top-risk consequences, unlock framing) + AA dashboard header; chore: drop sandbox .fuse_hidden junk"
echo --- push force ---
git push -u origin main --force
echo --- EXIT %errorlevel% ---
) > _deploy_out.txt 2>&1
type _deploy_out.txt | clip
echo (Output copied to clipboard.)
pause
