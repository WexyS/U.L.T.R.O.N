@echo off
title Ultron v2.1 — Desktop GUI Launcher
color 4C
echo.
echo ============================================================
echo  Ultron v2.1 — Personal AI Assistant (Desktop GUI)
echo  Multi-Agent - Voice Control - System Monitor
echo ============================================================
echo.

:: Set working directory to script location
cd /d "%~dp0"

:: Activate virtual environment
if exist "%~dp0.venv\Scripts\activate.bat" (
    call "%~dp0.venv\Scripts\activate.bat"
    echo [1/4] Virtual environment activated.
) else (
    echo [-] Virtual environment not found: .venv
    echo     Create one: python -m venv .venv ^&^& .venv\Scripts\pip install -e .
    pause
    exit /b 1
)

:: Check Ollama
echo [2/4] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Ollama is not running. Some features may not work.
    echo     Start Ollama: ollama serve
    echo     Pull model: ollama pull qwen2.5:14b
) else (
    echo      Ollama is running.
)

:: Check model
echo [3/4] Checking model (qwen2.5:14b)...
ollama list 2>&1 | findstr "qwen2.5:14b" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Model not found. Downloading qwen2.5:14b...
    ollama pull qwen2.5:14b
) else (
    echo      Model ready.
)

:: Launch Desktop GUI
echo [4/4] Starting Ultron Desktop Interface...
echo.
set PYTHONPATH="%~dp0"
"%~dp0.venv\Scripts\python.exe" -m ultron.desktop.app
echo.
pause
