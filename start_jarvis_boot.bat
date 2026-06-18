@echo off
:: ============================================================
::  J.A.R.V.I.S. BOOT LAUNCHER  (auto-start on logon)
::  Launches the full 8-service ecosystem + the voice GUI in the
::  interactive desktop session so audio works (no PaErrorCode -9999).
::  Called by Startup-folder VBS. No 'pause' so boot is unattended.
:: ============================================================
title J.A.R.V.I.S. Boot Launcher
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

set PY="C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe"
set JARVIS=C:\Users\HP\jarvis

echo Cleaning up any stale instances...
:: Kill ANY previous Jarvis GUI by command line (prevents duplicate instances
:: fighting over the microphone, regardless of how it was launched).
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" 2>nul
taskkill /f /im ollama.exe 2>nul
taskkill /f /fi "windowtitle eq J.A.R.V.I.S. Voice Assistant*" 2>nul
taskkill /f /fi "windowtitle eq Odysseus AI Server*" 2>nul
taskkill /f /fi "windowtitle eq AI Studio Backend*" 2>nul
taskkill /f /fi "windowtitle eq AI Studio Frontend*" 2>nul
taskkill /f /fi "windowtitle eq WhatsApp Forwarder*" 2>nul
taskkill /f /fi "windowtitle eq TypeScript Jarvis*" 2>nul
taskkill /f /fi "windowtitle eq Ollama Server*" 2>nul
call clawdbot gateway stop 2>nul
ping -n 3 127.0.0.1 > nul

echo [1/8] Ollama Server...
start "Ollama Server" /min /D "%JARVIS%\scratch\ollama" cmd /k "ollama serve"
ping -n 3 127.0.0.1 > nul

echo [2/8] Odysseus AI Server...
start "Odysseus AI Server" /min /D "%JARVIS%\scratch\odysseus" cmd /k "%PY% -m uvicorn app:app --host 127.0.0.1 --port 7000"
ping -n 3 127.0.0.1 > nul

echo [3/8] Moltbot Gateway...
start "Moltbot Gateway" /min /D "%JARVIS%" cmd /k "clawdbot gateway"
ping -n 3 127.0.0.1 > nul

echo [4/8] TypeScript Jarvis Daemon...
start "TypeScript Jarvis" /min /D "C:\Users\HP\jarvis_ts" cmd /k "set PATH=C:\Users\HP\.bun\bin;%%PATH%% && bun start"
ping -n 3 127.0.0.1 > nul

echo [5/8] AI Studio Backend...
start "AI Studio Backend" /min /D "E:\Muhammad's Work VP automation\full bot\vision-point-ai-studio-complete\backend" cmd /k "npm start"
ping -n 3 127.0.0.1 > nul

echo [6/8] AI Studio Frontend...
start "AI Studio Frontend" /min /D "E:\Muhammad's Work VP automation\full bot\vision-point-ai-studio-complete\frontend" cmd /k "npm run dev"
ping -n 3 127.0.0.1 > nul

echo [7/8] WhatsApp Forwarder...
start "WhatsApp Forwarder" /D "E:\Muhammad's Work VP automation\full bot\voice-automation my upgradation" cmd /k "node app.js"
ping -n 3 127.0.0.1 > nul

echo [8/8] J.A.R.V.I.S. Voice Assistant GUI...
start "J.A.R.V.I.S. Voice Assistant" /D "%JARVIS%" cmd /k "%PY% -u main.py"

echo All services launched.
