@echo off
setlocal enabledelayedexpansion
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
if exist ".ultron_pids.txt" (
    for /f "tokens=*" %%i in (.ultron_pids.txt) do (
        taskkill /F /PID %%i >nul 2>&1
    )
    del .ultron_pids.txt
)
:: Legacy cleanup for the first run or if pids file is missing
:: taskkill /F /FI "WINDOWTITLE eq Ultron*" >nul 2>&1
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

:: [1.5/4] Brain Activation
echo [+] Ultron Genesis Brain (8001) uyandiriliyor... [TURBO MODE: 4-BIT]
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "FACTORY_DIR=%~dp0Ultron Factory"
start "Ultron Brain" /D "%FACTORY_DIR%" cmd /k set API_PORT=8001 ^&^& "%PYTHON_EXE%" -m ultronfactory.cli api --model_name_or_path models/Qwen2.5-14B --adapter_name_or_path saves/Qwen2.5-14B/lora/ultron_brain_v1 --template qwen --finetuning_type lora --quantization_bit 4

:: Record Brain PID
timeout /t 3 >nul
for /f "tokens=2" %%i in ('tasklist /fi "windowtitle eq Ultron Brain" /fo csv /nh') do (
    set "PID=%%~i"
    echo !PID! >> .ultron_pids.txt
)

:: Wait for Port 8001 (Brain)
echo [+] Ultron Brain (8001) hazir olmasi bekleniyor...
powershell -Command "$retry=0; while($retry -lt 120) { try { $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8001); if($c.Connected) { $c.Close(); exit 0 } } catch { $retry++; Start-Sleep -Milliseconds 500 } }; exit 1"
if errorlevel 1 (
    echo [!] UYARI: Ultron Brain (8001) gecikmeli basliyor veya hata aldi. Devam ediliyor...
) else (
    echo [OK] Ultron Brain aktif.
)

:: [2/4] Backend
echo [+] Backend (8000) baslatiliyor... [GLOBAL ACCESSIBLE: 0.0.0.0]
start "Ultron Backend" /D "%~dp0." cmd /k "%PYTHON_EXE%" -m uvicorn ultron.api.main:app --host 0.0.0.0 --port 8000

:: Record Backend PID
timeout /t 2 >nul
for /f "tokens=2" %%i in ('tasklist /fi "windowtitle eq Ultron Backend" /fo csv /nh') do (
    set "PID=%%~i"
    echo !PID! >> .ultron_pids.txt
)

:: [3/4] Wait for Port 8000 (Backend)
echo [+] Backend (8000) bekleniyor...
powershell -Command "$retry=0; while($retry -lt 60) { try { $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8000); if($c.Connected) { $c.Close(); exit 0 } } catch { $retry++; Start-Sleep -Milliseconds 500 } }; exit 1"
if errorlevel 1 (
    echo [-] HATA: Backend (8000) zaman asimina ugradi. 
    pause
    exit /b 1
)
echo [OK] Backend hazir.

:: [4/4] Frontend and Voice
echo [+] Sesli asistan ve Arayuz baslatiliyor...
start "Ultron Voice" /min /D "%~dp0." cmd /k "%PYTHON_EXE%" -m ultron.voice_app

:: Record Voice PID
for /f "tokens=2" %%i in ('tasklist /fi "windowtitle eq Ultron Voice" /fo csv /nh') do (
    set "PID=%%~i"
    echo !PID! >> .ultron_pids.txt
)

cd ultron-desktop
if not exist "node_modules\" (
    echo [+] Dependencies yukleniyor (bu ilk seferde vakit alabilir)...
    call npm install
)

echo [+] Arayuz baslatiliyor... [GLOBAL ACCESSIBLE: 0.0.0.0]
start "Ultron Frontend" cmd /c "npm run dev -- --host 0.0.0.0"

:: Record Frontend PID
for /f "tokens=2" %%i in ('tasklist /fi "windowtitle eq Ultron Frontend" /fo csv /nh') do (
    set "PID=%%~i"
    echo !PID! >> .ultron_pids.txt
)

:: Wait for Vite to be ready (Port 5173)
echo [+] Frontend (5173) bekleniyor...
powershell -Command "$retry=0; while($retry -lt 60) { try { $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 5173); if($c.Connected) { $c.Close(); exit 0 } } catch { $retry++; Start-Sleep -Milliseconds 500 } }; exit 1"
if errorlevel 1 (
    echo [-] HATA: Frontend (5173) 60 saniyede baslamadi.
    pause
    exit /b 1
)

echo [OK] Frontend hazir.

:: [5/4] Ngrok Integration (Optional)
where ngrok >nul 2>&1
if %errorlevel% equ 0 (
    echo [+] Ngrok bulundu, tünel aciliyor...
    :: Check if tunnel already running
    tasklist /fi "windowtitle eq Ultron Ngrok" /fo csv /nh | findstr /i "ngrok" >nul
    if errorlevel 1 (
        start "Ultron Ngrok" /min cmd /k "ngrok http 5173"
        timeout /t 3 >nul
        echo [+] Ngrok URL .env dosyasina isleniyor...
        powershell -Command "try { $r=(Invoke-WebRequest 'http://localhost:4040/api/tunnels' -UseBasicParsing).Content | ConvertFrom-Json; $url=$r.tunnels[0].public_url; if($url) { (Get-Content ../.env) -replace '^NGROK_URL=.*','NGROK_URL='+$url | Set-Content ../.env; echo \"[NGROK] $url\"; } } catch { echo \"[NGROK] Tünel bilgisi henüz hazir degil.\" }"
    )
) else (
    echo [i] Ngrok bulunmadi. Uzaktan erisim icin: https://ngrok.com
)

echo [+] Ultron Arayuzu aciliyor... (Lutfen 5 saniye bekleyin)
timeout /t 5 >nul
start http://localhost:5173

echo.
echo ============================================================
echo   ULTRON AGI SISTEMI AKTIF VE TURBO MODDA! 🚀
echo ============================================================
echo.
echo [+] Tum sistemler devrede. Iyi calismalar Eren! 🦾
pause

