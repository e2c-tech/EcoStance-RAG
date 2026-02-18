# Setup EcoStance Local Development
# This script creates virtual environments and installs dependencies for all services.

Write-Host "Setting up EcoStance Local Development Environment..." -ForegroundColor Cyan

# 1. Setup Ecostance Agent Backend
Write-Host "`n--- Setting up Ecostance Agent Backend ---" -ForegroundColor Yellow
Set-Location w:\ecostance-rag-docker\ecostance-agent-v1
if (!(Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}
Write-Host "Installing requirements..."
. .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m nltk.downloader punkt punkt_tab
Set-Location ..

# 3. Setup Ecostance UI Frontend
Write-Host "`n--- Setting up Ecostance UI Frontend ---" -ForegroundColor Yellow
Set-Location w:\ecostance-rag-docker\ecostance-ui-v1
Write-Host "Installing npm packages..."
npm install
Set-Location ..

Write-Host "`nSetup complete! You can now run the environment using ./run-local.ps1" -ForegroundColor Cyan
