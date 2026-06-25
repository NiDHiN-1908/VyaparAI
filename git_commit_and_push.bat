@echo off
title VyaparAI Git Commit Helper
color 0A
echo ===================================================
echo   VyaparAI Git Commit and Push Helper
echo ===================================================
echo.
echo [1/3] Staging changes...
git add backend/main.py backend/routers/youtube_monitor.py walkthrough.md
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to stage files. Is Git installed and initialized in this directory?
    pause
    exit /b %ERRORLEVEL%
)
echo   ^/[x^] Files staged successfully.
echo.
echo [2/3] Committing changes...
git commit -m "Fix video monitoring dashboard socket hang and seed fallback videos"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to commit changes.
    pause
    exit /b %ERRORLEVEL%
)
echo   ^/[x^] Changes committed successfully.
echo.
echo [3/3] Pushing to GitHub...
git push
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to push changes.
    pause
    exit /b %ERRORLEVEL%
)
echo   ^/[x^] Changes pushed to GitHub successfully!
echo.
echo ===================================================
echo Commit and Push complete!
echo ===================================================
echo.
pause
