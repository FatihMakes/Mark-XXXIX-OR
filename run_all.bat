@echo off
title J.A.R.V.I.S. Ecosystem Launcher

echo ====================================================
echo      J.A.R.V.I.S. ECOSYSTEM SERVICES LAUNCHER
echo ====================================================
echo.

echo Stopping any running Ollama instances...
taskkill /f /im ollama.exe 2>nul
ping -n 2 127.0.0.1 > nul

echo Stopping any running J.A.R.V.I.S. Ecosystem windows...
taskkill /f /fi "windowtitle eq J.A.R.V.I.S. Voice Assistant*" 2>nul
taskkill /f /fi "windowtitle eq Odysseus AI Server*" 2>nul
taskkill /f /fi "windowtitle eq AI Studio Backend*" 2>nul
taskkill /f /fi "windowtitle eq AI Studio Frontend*" 2>nul
taskkill /f /fi "windowtitle eq WhatsApp Forwarder*" 2>nul
taskkill /f /fi "windowtitle eq TypeScript Jarvis*" 2>nul
taskkill /f /fi "windowtitle eq Ollama Server*" 2>nul
ping -n 2 127.0.0.1 > nul

echo Stopping any running Moltbot Gateway instance...
call clawdbot gateway stop
ping -n 2 127.0.0.1 > nul

echo [1/8] Starting Ollama Server...
start "Ollama Server" /D "C:\Users\HP\jarvis\scratch\ollama" cmd /k "ollama serve"
ping -n 3 127.0.0.1 > nul

echo [2/8] Starting Odysseus AI Server...
start "Odysseus AI Server" /D "C:\Users\HP\jarvis\scratch\odysseus" cmd /k ""C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 7000"
ping -n 3 127.0.0.1 > nul

echo [3/8] Starting Moltbot Gateway...
start "Moltbot Gateway" /D "C:\Users\HP\jarvis" cmd /k "clawdbot gateway"
ping -n 3 127.0.0.1 > nul

echo [4/8] Starting TypeScript Jarvis Daemon...
start "TypeScript Jarvis" /D "C:\Users\HP\jarvis_ts" cmd /k "set PATH=C:\Users\HP\.bun\bin;%%PATH%% && bun start"
ping -n 3 127.0.0.1 > nul

echo [5/8] Starting AI Studio Backend...
start "AI Studio Backend" /D "E:\Muhammad's Work VP automation\full bot\vision-point-ai-studio-complete\backend" cmd /k "npm start"
ping -n 3 127.0.0.1 > nul

echo [6/8] Starting AI Studio Frontend...
start "AI Studio Frontend" /D "E:\Muhammad's Work VP automation\full bot\vision-point-ai-studio-complete\frontend" cmd /k "npm run dev"
ping -n 3 127.0.0.1 > nul

echo [7/8] Starting WhatsApp Forwarder...
start "WhatsApp Forwarder" /D "E:\Muhammad's Work VP automation\full bot\voice-automation my upgradation" cmd /k "node app.js"
ping -n 3 127.0.0.1 > nul

echo [8/8] Starting Python J.A.R.V.I.S. Voice Assistant GUI...
start "J.A.R.V.I.S. Voice Assistant" /D "C:\Users\HP\jarvis" cmd /k ""C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe" -u main.py"
ping -n 3 127.0.0.1 > nul

echo.
echo ====================================================
echo      ALL SERVICES LAUNCHED SUCCESSFULLY!
echo ====================================================
echo.
echo You can check the open terminal windows to monitor logs.
echo If you need to log into Moltbot's WhatsApp, open a new CMD and run: clawdbot channels login
echo.
echo Press any key to close this launcher window.
pause > nul
