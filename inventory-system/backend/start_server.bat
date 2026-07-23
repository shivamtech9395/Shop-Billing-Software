@echo off
cd /d %~dp0
echo Starting Dukaan Manager server...
echo.
echo Browser mein yeh kholein: http://localhost:8090
echo.
uvicorn main:app --host 0.0.0.0 --port 8090
pause
