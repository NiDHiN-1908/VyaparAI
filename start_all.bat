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
rem 1. Check if Ollama is already listening on port 11434
netstat -ano | findstr LISTENING | findstr :11434 >nul
if not errorlevel 1 (
    echo   ^/[x^] Ollama is already running and listening on port 11434.
    goto ollama_ok
)

rem 2. Try starting local Ollama if installed
if not exist "%LocalAppData%\Programs\Ollama\ollama app.exe" goto no_local_ollama
echo   [WARNING] Local Ollama is installed but not running. Launching it...
start "" "%LocalAppData%\Programs\Ollama\ollama app.exe"
echo   * Waiting up to 10 seconds for Ollama to initialize...
set "WAIT_COUNT=0"

:wait_ollama_loop
timeout /t 1 /nobreak > nul
netstat -ano | findstr LISTENING | findstr :11434 >nul
if not errorlevel 1 (
    echo   ^/[x^] Ollama Local LLM runner launched and listening on port 11434.
    goto ollama_ok
)
set /a "WAIT_COUNT+=1"
if %WAIT_COUNT% lss 10 goto wait_ollama_loop
echo   [WARNING] Ollama launched but failed to respond on port 11434 in 10 seconds.

:no_local_ollama
rem 3. Check Docker status
docker info >nul 2>&1
if errorlevel 1 (
    echo   [WARNING] Ollama local runner not detected, and Docker is offline. AI responses will be rule-based.
    goto ollama_ok
)

rem 4. Docker is online, try starting Ollama container
echo   [WARNING] Local Ollama not detected. Starting Ollama container...
docker compose -f docker\docker-compose.yml up -d ollama
echo   * Waiting up to 10 seconds for Ollama container to warm up...
set "WAIT_COUNT=0"

:wait_docker_ollama_loop
timeout /t 1 /nobreak > nul
netstat -ano | findstr LISTENING | findstr :11434 >nul
if not errorlevel 1 (
    echo   ^/[x^] Ollama container is running and listening.
    goto docker_ollama_pull
)
set /a "WAIT_COUNT+=1"
if %WAIT_COUNT% lss 10 goto wait_docker_ollama_loop
echo   [WARNING] Ollama container started but failed to respond on port 11434 in 10 seconds.
goto ollama_ok

:docker_ollama_pull
echo   * Ensuring model 'llama3.1' is pulled in Docker...
docker exec vyaparai_ollama ollama pull llama3.1

:ollama_ok
echo.
echo   * Checking WhatsApp Evolution API...
docker info >nul 2>&1
if errorlevel 1 (
    echo   [WARNING] Docker Desktop is not running. WhatsApp integration will be offline.
    goto evolution_ok
)

docker ps --filter "name=vyaparai_evolution_api" --filter "status=running" | find /i "vyaparai_evolution_api" > nul
if not errorlevel 1 (
    echo   ^/[x^] Evolution API WhatsApp container is already running.
    goto evolution_ok
)

echo   [WARNING] Evolution API container is not running. Starting it...
docker compose -f docker\docker-compose.yml up -d evolution-api

:evolution_ok
echo.
echo [2/3] Launching servers and tunnels in parallel windows...
echo   * Launching Public SSH Tunnel...
start "VyaparAI SSH Tunnel" cmd /k "backend\venv\Scripts\python.exe backend\start_tunnel.py"
echo     Waiting 3 seconds for tunnel configuration to sync...
timeout /t 3 /nobreak > nul

echo   * Launching FastAPI Backend on http://localhost:8000/
start "VyaparAI Backend Server" cmd /k "backend\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"


echo   * Launching Next.js Frontend on http://localhost:3000/
start "VyaparAI Frontend App" cmd /k "cd frontend && npm run dev"

echo.
echo [3/3] Preparing workspace browser view...
echo   * Waiting for compilers to initialize (4 seconds)...
timeout /t 4 /nobreak > nul

echo   * Launching default browser to Comment Inbox...
start "" "http://localhost:3000/comment-inbox"

echo.
echo ===================================================
echo VyaparAI Suite initialized! Keep this window open
echo if you need to shut down processes later, or close
echo it once your browser has opened.
echo ===================================================
echo.
pause
