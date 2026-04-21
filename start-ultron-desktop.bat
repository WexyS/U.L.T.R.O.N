@echo off
setlocal enabledelayedexpansion
title Ultron AGI — Unified Master Launcher
color 0B

echo.
echo ============================================================
echo   ULTRON AGI v3.0 - MASTER UNIFIED LAUNCHER
echo ============================================================
echo.

cd /d "%~dp0"

:: [0/4] Cleanup Ghost Processes
echo [+] Eski surecler temizleniyor...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1
timeout /t 1 >nul

:: [1/4] Activate Environment
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo [+] Sanal ortam aktif edildi.
) else (
    echo [-] HATA: .venv bulunamadı!
    pause & exit /b 1
)

:: [2/4] Start Backend (Optimized)
echo [+] Backend (Port 8000) baslatiliyor...
start "Ultron Backend" /min cmd /k "python -m uvicorn ultron.api.main:app --host 0.0.0.0 --port 8000 --no-access-log --workers 1"

:: [3/4] Wait for Backend
echo [+] Backend bekleniyor...
set RETRY=0
:HEALTH_LOOP
    timeout /t 1 /nobreak >nul
    curl -sf http://127.0.0.1:8000/health >nul 2>&1
    if !errorlevel! equ 0 goto BACKEND_OK
    set /a RETRY+=1
    if !RETRY! lss 30 goto HEALTH_LOOP
    echo [-] HATA: Backend baslamadi! Lutfen port 8000'i kontrol edin.
    pause & exit /b 1
:BACKEND_OK
echo [OK] Backend hazir.

:: [4/4] Start Voice & Frontend
echo [+] Sesli asistan ve Arayuz baslatiliyor...
start "Ultron Voice" /min cmd /c "python -m ultron.voice_app"
cd ultron-desktop
start /b cmd /c "npm run dev"

echo.
echo ============================================================
echo   ULTRON AGI SISTEMI AKTIF! ✨🚀
echo   Dashboard: https://127.0.0.1:5174
echo ============================================================
echo.

:: Open Dashboard
timeout /t 3 >nul
start https://127.0.0.1:5174

:: Keep alive
pause >nul
