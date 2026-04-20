@echo off
title Ultron Remote Access (ngrok)
echo ==========================================
echo    ULTRON REMOTE ACCESS BOOSTER (ngrok)
echo ==========================================
echo.
echo [1] Ngrok yüklü mü kontrol ediliyor...
where ngrok >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] HATA: ngrok bulunamadı! 
    echo Lütfen https://ngrok.com adresinden indirip PATH'e ekleyin.
    pause
    exit /b
)

echo [2] Ultron Backend (8000) dış dünyaya açılıyor...
echo Arkadaşlarına göndereceğin link birazdan aşağıda belirecek.
echo.
echo IP adresi ve port forwarding ile uğraşmana gerek kalmadı! 😉
echo.
ngrok http 8000
pause
