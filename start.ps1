<#
.SYNOPSIS
    Waiting The Longest - Quick Start Script (PowerShell)
.DESCRIPTION
    Sets up and runs the development environment with a single command.
.EXAMPLE
    .\start.ps1
    .\start.ps1 -Setup    # Force re-run setup
    .\start.ps1 -Port 8080
#>

param(
    [switch]$Setup,
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Waiting The Longest - Quick Start" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to project root
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://python.org" -ForegroundColor Yellow
    exit 1
}

# Check if venv exists
$VenvPath = Join-Path $ProjectRoot "backend\.venv"
$NeedsSetup = $Setup -or (-not (Test-Path $VenvPath))

if ($NeedsSetup) {
    Write-Host "Setting up development environment..." -ForegroundColor Yellow
    python scripts\dev_setup.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Setup failed!" -ForegroundColor Red
        exit 1
    }
}

# Start the server
Write-Host ""
Write-Host "Starting development server on port $Port..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

$RunArgs = @("scripts\run.py", "--port", $Port)
if (-not $NoBrowser) {
    $RunArgs += "--open"
}

python @RunArgs
