@echo off
echo ==============================================
echo          Port 8000 Diagnostic Tool
echo ==============================================
echo.

echo Checking what is running on port 8000...
echo (If nothing is displayed below, port 8000 is free)
echo.
netstat -ano | findstr :8000

echo.
echo If a process is shown above, the last number in the row is the Process ID (PID).
echo You can terminate it by running the following command in an Administrator command prompt:
echo   taskkill /F /PID [PID]
echo.
echo If a Docker container is running on port 8000, you can stop it using:
echo   docker ps
echo   docker stop [container_id_or_name]
echo.
pause
