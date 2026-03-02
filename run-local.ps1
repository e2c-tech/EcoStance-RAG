# Start EcoStance Local Development
# This script starts all services without Docker.

Write-Host "Starting EcoStance Local Development Environment..." -ForegroundColor Cyan

# 1. Load Root .env file
if (Test-Path ".env") {
    Write-Host "Loading .env file..." -ForegroundColor Green
    foreach ($line in Get-Content .env) {
        if ($line -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# 2. Start Ecostance Agent Backend (Port 9007)
Write-Host "Starting Ecostance Agent Backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd ecostance-agent-v1; . .venv\Scripts\activate; uvicorn app.main:app --host 0.0.0.0 --port 9007" -WindowStyle Normal

# 3. Start Ecostance UI Frontend (Port 9008)
Write-Host "Starting Ecostance UI Frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd ecostance-ui-v1; npm run dev -- --port 9008" -WindowStyle Normal

Write-Host "`nAll services are starting in separate windows." -ForegroundColor Cyan
Write-Host "Agent Backend: http://localhost:9007"
Write-Host "Agent UI:      http://localhost:9008"
Write-Host "`nMaintain this window to keep environment variables if needed, or close it after services start."
