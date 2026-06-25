# Start J.A.R.V.I.S. Ecosystem Services

Write-Host "Stopping any running Ollama instances..." -ForegroundColor Yellow
Stop-Process -Name "ollama" -ErrorAction SilentlyContinue

Write-Host "Starting Ollama Server..." -ForegroundColor Cyan
Start-Process -FilePath "C:\Users\HP\jarvis\scratch\ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden -WorkingDirectory "C:\Users\HP\jarvis\scratch\ollama"

Write-Host "Starting Odysseus AI Server..." -ForegroundColor Cyan
Start-Process -FilePath "C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe" -ArgumentList "-m uvicorn app:app --host 127.0.0.1 --port 7000" -WindowStyle Hidden -WorkingDirectory "C:\Users\HP\jarvis\scratch\odysseus"

Write-Host "Starting Moltbot Gateway..." -ForegroundColor Cyan
Start-Process -FilePath "clawdbot" -ArgumentList "gateway" -WindowStyle Hidden -WorkingDirectory "C:\Users\HP\jarvis"

Write-Host "Starting TypeScript Jarvis..." -ForegroundColor Cyan
$env:PATH="C:\Users\HP\.bun\bin;" + $env:PATH
Start-Process -FilePath "bun" -ArgumentList "start" -WindowStyle Hidden -WorkingDirectory "C:\Users\HP\jarvis_ts"

Write-Host "Starting AI Studio Backend..." -ForegroundColor Cyan
Start-Process -FilePath "npm" -ArgumentList "start" -WindowStyle Hidden -WorkingDirectory "E:\Muhammad's Work VP automation\full bot\vision-point-ai-studio-complete\backend"

Write-Host "Starting AI Studio Frontend..." -ForegroundColor Cyan
Start-Process -FilePath "npm" -ArgumentList "run dev" -WindowStyle Hidden -WorkingDirectory "E:\Muhammad's Work VP automation\full bot\vision-point-ai-studio-complete\frontend"

Write-Host "Starting WhatsApp Forwarder..." -ForegroundColor Cyan
# Start node app.js in a normal/visible window so that QR code renders correctly
Start-Process -FilePath "node" -ArgumentList "app.js" -WorkingDirectory "E:\Muhammad's Work VP automation\full bot\voice-automation my upgradation"

Write-Host "Starting Main Python J.A.R.V.I.S. Assistant GUI..." -ForegroundColor Green
Start-Process -FilePath "C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe" -ArgumentList "main.py" -WorkingDirectory "C:\Users\HP\jarvis"

Write-Host "All services successfully launched!" -ForegroundColor Green
