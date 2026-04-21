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

:: [1.5/4] Brain Check (Optional)
echo [+] Ultron Brain (8001) kontrol ediliyor...
powershell -Command "$c = New-Object System.Net.Sockets.TcpClient; try { $c.Connect('127.0.0.1', 8001); if($c.Connected) { write-host '[OK] Ultron Brain aktif.'; $c.Close(); exit 0 } } catch { write-host '[?] UYARI: Ultron Brain (8001) bulunamadi. Yerel model pasif olabilir.'; exit 0 }"

:: [2/4] Backend
echo [+] Backend (8000) baslatiliyor...
:: Start backend in a separate visible window for debugging
start "Ultron Backend" cmd /k "python -m uvicorn ultron.api.main:app --host 127.0.0.1 --port 8000"

:: [3/4] Wait for Port 8000 (Backend)
echo [+] Backend (8000) bekleniyor...
powershell -Command "$retry=0; while($retry -lt 45) { try { $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8000); if($c.Connected) { $c.Close(); exit 0 } } catch { $retry++; Start-Sleep -Seconds 2 } }; exit 1"
if errorlevel 1 (
    echo [-] HATA: Backend (8000) zaman asimina ugradi. 
    echo Lutfen acilan backend penceresindeki hatalari kontrol edin.
    pause
    exit /b 1
)
echo [OK] Backend hazir.

:: [4/4] Frontend and Voice
echo [+] Sesli asistan ve Arayuz baslatiliyor...
start "Ultron Voice" /min cmd /c "python -m ultron.voice_app"

cd ultron-desktop
if not exist "node_modules\" (
    echo [+] Dependencies yukleniyor (bu ilk seferde vakit alabilir)...
    call npm install
)

echo [+] Arayuz baslatiliyor...
start "Ultron Frontend" cmd /c "npm run dev"

echo.
echo ============================================================
echo   ULTRON AGI SISTEMI AKTIF. 
echo ============================================================
echo.

:: Wait a bit for Vite to start and then launch browser
timeout /t 5 >nul
start http://localhost:5173

echo [+] Tum sistemler devrede.
pause
