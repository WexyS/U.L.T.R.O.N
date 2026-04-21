@echo off
title Ultron AGI - Unified Master Launcher
color 0B

echo.
echo ============================================================
echo   ULTRON AGI v3.0 - MASTER UNIFIED LAUNCHER
echo ============================================================
echo.

cd /d "%~dp0"

:: [0/4] Cleanup
echo [+] Eski surecler temizleniyor...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1
timeout /t 1 >nul

:: [1/4] Environment
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo [+] Sanal ortam aktif.
) else (
    echo [-] HATA: .venv bulunamadi.
    pause
    exit /b 1
)

:: [1.5/4] Brain Check
echo [+] Ultron Brain (8001) kontrol ediliyor...
netstat -ano | findstr :8001 >nul 2>&1
if not errorlevel 1 (
    echo [OK] Ultron Brain aktif.
) else (
    echo [?] UYARI: Ultron Brain bulunamadi.
)

:: [2/4] Backend
echo [+] Backend (8000) baslatiliyor...
:: Start backend in a visible window for debugging if it fails
start "Ultron Backend" cmd /k "python -m uvicorn ultron.api.main:app --host 0.0.0.0 --port 8000"

:: [3/4] Wait
echo [+] Backend bekleniyor...
set RETRY=0
:HEALTH_LOOP
    timeout /t 2 /nobreak >nul
    curl -sf http://127.0.0.1:8000/health >nul 2>&1
    if not errorlevel 1 goto BACKEND_OK
    set /a RETRY+=1
    if %RETRY% lss 20 goto HEALTH_LOOP
    echo [-] HATA: Backend baslamadi.
    pause
    exit /b 1
:BACKEND_OK
echo [OK] Backend hazir.

:: [4/4] Others
echo [+] Sesli asistan ve Arayuz baslatiliyor...
start "Ultron Voice" /min cmd /c "python -m ultron.voice_app"
cd ultron-desktop
start /b cmd /c "npm run dev"

echo.
echo ============================================================
echo   ULTRON AGI SISTEMI AKTIF. 
echo ============================================================
echo.

timeout /t 3 >nul
start https://127.0.0.1:5174
pause
