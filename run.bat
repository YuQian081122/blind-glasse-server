@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 4000 --log-level warning --no-access-log
) else (
  echo [錯誤] 找不到 .venv，請先執行：
  echo   python -m venv .venv
  echo   .venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)
pause
