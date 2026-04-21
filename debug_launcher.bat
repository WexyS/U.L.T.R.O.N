@echo on
title Ultron Debug Launcher - Verbose Mode
cd /d "%~dp0"

echo [+] Environment Check...
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [!] HATA: .venv bulunamadi!
    pause
    exit /b 1
)

echo [+] Port 8001 (Brain) Check...
netstat -ano | findstr :8001

echo [+] Port 8000 (Backend) Check...
netstat -ano | findstr :8000

echo [+] Starting Backend in Verbose Mode...
:: Set DEBUG env var if needed
set DEBUG=1
python -m uvicorn ultron.api.main:app --host 127.0.0.1 --port 8000 --log-level debug

pause
