#!/usr/bin/env pwsh
# ===============================================================================
# Waiting The Longest™ - PowerShell Development Setup Script
# ===============================================================================
# Purpose: Set up local development environment on Windows
# Usage: .\scripts\dev-setup.ps1
# ===============================================================================

param(
    [switch]$SkipVenv,
    [switch]$SkipDeps,
    [switch]$SkipDb
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check Python installation
Write-Step "Checking Python installation..."
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python not found. Please install Python 3.10+ from https://python.org"
    exit 1
}
Write-Success "Found $pythonVersion"

# Create virtual environment
if (-not $SkipVenv) {
    Write-Step "Setting up virtual environment..."
    
    if (Test-Path "venv") {
        Write-Success "Virtual environment already exists"
    } else {
        python -m venv venv
        Write-Success "Virtual environment created"
    }
    
    # Activate
    & .\venv\Scripts\Activate.ps1
    Write-Success "Virtual environment activated"
}

# Install dependencies
if (-not $SkipDeps) {
    Write-Step "Installing Python dependencies..."
    
    pip install --upgrade pip | Out-Null
    pip install -r backend\requirements.txt
    
    # Dev dependencies
    pip install pytest pytest-asyncio pytest-cov httpx black isort flake8 faker
    
    Write-Success "Dependencies installed"
}

# Set up environment file
Write-Step "Setting up environment file..."
if (Test-Path ".env") {
    Write-Success ".env file already exists"
} elseif (Test-Path ".env.example") {
    Copy-Item .env.example .env
    Write-Success ".env file created from template"
    Write-Warning "Please edit .env and add your API keys"
} else {
    Write-Warning "No .env.example found"
}

# Initialize database
if (-not $SkipDb) {
    Write-Step "Initializing database..."
    
    Push-Location backend
    
    python -c @"
from app.database import engine, Base
from app.models import Animal, Shelter, SuccessStory, NewsletterSubscriber
Base.metadata.create_all(bind=engine)
print('Database tables created')
"@
    
    Pop-Location
    
    Write-Success "Database initialized"
}

# Print summary
Write-Host "`n===============================================" -ForegroundColor Green
Write-Host "Development Setup Complete!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Activate the virtual environment (if not already):"
Write-Host "   .\venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "2. Edit .env with your API keys:"
Write-Host "   notepad .env"
Write-Host ""
Write-Host "3. Start the development server:"
Write-Host "   cd backend"
Write-Host "   uvicorn app.main:app --reload"
Write-Host ""
Write-Host "4. Open in browser:"
Write-Host "   http://localhost:8000"
Write-Host ""
Write-Host "5. Run tests:"
Write-Host "   cd backend && pytest"
Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
