@echo off
cd /d "%~dp0"
python -m uvicorn main:app --host 0.0.0.0 --port 5000 --log-level warning --no-access-log
pause
