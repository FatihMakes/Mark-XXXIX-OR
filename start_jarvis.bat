@echo off
:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run
) else (
    echo Requesting Administrative Elevation (UAC)...
    powershell -Command "Start-Process -FilePath '%0' -ArgumentList 'elevated' -Verb RunAs"
    exit /b
)

:run
title JARVIS Mark XXXIX-OR
cd /d "C:\Users\HP\jarvis"
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
echo Starting JARVIS Mark XXXIX-OR with Administrative privileges...
"C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe" main.py
pause
