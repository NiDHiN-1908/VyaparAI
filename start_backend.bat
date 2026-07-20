@echo off
echo ==============================================
echo        VyaparAI Backend Server Launcher
echo ==============================================
echo.

cd /d "%~dp0"

if not exist "backend\venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment venv not found in backend directory!
    echo Please make sure you have run the setup instructions.
    echo.
    pause
    exit /b 1
)

echo Activating Python Virtual Environment...
call backend\venv\Scripts\activate

echo.
echo Starting backend server via uvicorn...
echo Access the API at http://127.0.0.1:8000/
echo Access the API docs at http://127.0.0.1:8000/docs
echo.

backend\venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The server exited with error code %errorlevel%.
    echo This might be due to:
    echo   1. Port conflict: Another process (or docker) is already using port 8000.
    echo   2. Missing dependencies: Run 'pip install -r requirements.txt' inside the backend virtual environment.
    echo.
)

pause
