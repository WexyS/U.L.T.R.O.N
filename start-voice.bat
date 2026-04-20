@echo off
title Ultron Voice Assistant (Orb)
echo ==========================================
echo    ULTRON VOICE ASSISTANT - STANDALONE
echo ==========================================
echo.
echo [1] Ortam degiskenleri hazirlaniyor...
set PYTHONPATH=%PYTHONPATH%;%CD%

echo [2] Sanal ortam aktif ediliyor...
if exist .venv\Scripts\activate (
    call .venv\Scripts\activate
) else if exist .ultron-venv\Scripts\activate (
    call .ultron-venv\Scripts\activate
) else (
    echo [!] HATA: Sanal ortam bulunamadi!
    pause
    exit /b
)

echo [3] Ultron Orb GUI baslatiliyor...
echo Lütfen bekleyin, sesli asistan yukleniyor...
start "" /B pythonw -m ultron.desktop.app
exit

if %errorlevel% neq 0 (
    echo.
    echo [!] Sesli asistan bir hata ile karsilasti.
    echo Lütfen PyAudio ve PyQt6 kütüphanelerinin kurulu oldugundan emin olun.
    pause
)
