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

echo [2] Ultron Dashboard (5174) dış dünyaya açılıyor...
echo Telefonundan gireceğin link birazdan aşağıda belirecek.
echo.
echo NOT: Vite HTTPS kullandığı için ngrok linkine girdiğinde
echo bir güvenlik uyarısı alırsan "Gelişmiş -> Devam Et" diyebilirsin. 😉
echo.
ngrok http https://localhost:5174
pause
