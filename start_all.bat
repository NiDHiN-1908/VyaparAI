@echo off
set "PATH=%SystemRoot%\System32;%SystemRoot%;%SystemRoot%\System32\Wbem;%SystemRoot%\System32\WindowsPowerShell\v1.0\;%PATH%"
title VyaparAI Dev Suite Launcher
color 0B
echo ===================================================
echo            V Y A P A R   A I
echo          --- Dev Suite Launcher ---
echo ===================================================
echo.
echo [1/3] Checking background dependencies...
set "OLLAMA_LOCAL_RUNNING=0"
tasklist /FI "IMAGENAME eq ollama_app.exe" 2>NUL | find /I /N "ollama_app.exe">NUL
if not errorlevel 1 (
    set "OLLAMA_LOCAL_RUNNING=1"
    echo   ^/[x^] Ollama Local LLM runner (app) is already running.
) else (
    tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL ^| find /I /N "ollama.exe">NUL
    if not errorlevel 1 (
        set "OLLAMA_LOCAL_RUNNING=1"
        echo   ^/[x^] Ollama Local LLM runner (process) is already running.
    )
)

if "%OLLAMA_LOCAL_RUNNING%"=="0" (
    docker info >nul 2>&1
    if not errorlevel 1 (
        docker ps --filter "name=vyaparai_ollama" --filter "status=running" ^| find /i "vyaparai_ollama" > nul
        if not errorlevel 1 (
            echo   ^/[x^] Ollama Docker container is already running.
        ) else (
            echo   [WARNING] Local Ollama not detected. Starting Ollama container...
            docker compose -f docker\docker-compose.yml up -d ollama
            echo   * Waiting 5 seconds for Ollama container to warm up...
            timeout /t 5 /nobreak > nul
        )
        echo   * Ensuring model 'llama3.1' is pulled in Docker...
        docker exec vyaparai_ollama ollama pull llama3.1
    ) else (
        echo   [WARNING] Ollama local runner not detected, and Docker is offline. AI responses will be rule-based.
    )
)
echo.
echo   * Checking WhatsApp Evolution API...
docker info >nul 2>&1
if not errorlevel 1 (
    docker ps --filter "name=vyaparai_evolution_api" --filter "status=running" ^| find /i "vyaparai_evolution_api" > nul
    if not errorlevel 1 (
        echo   ^/[x^] Evolution API WhatsApp container is already running.
    ) else (
        echo   [WARNING] Evolution API container is not running. Starting it...
        docker compose -f docker\docker-compose.yml up -d evolution-api
    )
) else (
    echo   [WARNING] Docker Desktop is not running. WhatsApp integration will be offline.
)
echo.
echo [2/3] Launching servers in parallel windows...
echo   * Launching FastAPI Backend on http://localhost:8000/
start "VyaparAI Backend Server" cmd /k "backend\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

echo   * Launching Next.js Frontend on http://localhost:3000/
start "VyaparAI Frontend App" cmd /k "cd frontend && npm run dev"

echo.
echo [3/3] Preparing workspace browser view...
echo   * Waiting for compilers to initialize (4 seconds)...
timeout /t 4 /nobreak > nul

echo   * Launching default browser to Comment Inbox...
start http://localhost:3000/comment-inbox

echo.
echo ===================================================
echo VyaparAI Suite initialized! Keep this window open
echo if you need to shut down processes later, or close
echo it once your browser has opened.
echo ===================================================
echo.
pause
