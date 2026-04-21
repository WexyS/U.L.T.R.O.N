@echo on
title Ultron Debug Launcher
cd /d "%~dp0"
echo Checking .venv...
if exist ".venv\Scripts\activate.bat" (
    echo Activating .venv...
    call ".venv\Scripts\activate.bat"
) else (
    echo HATA: .venv bulunamadi!
    pause
    exit /b 1
)
pause
echo Checking Brain Port 8001...
netstat -ano | findstr :8001
pause
echo Starting Backend...
python -m uvicorn ultron.api.main:app --host 127.0.0.1 --port 8000
pause
