# ============================================================================
# Best Friends Network Scraper - PowerShell Runner
# ============================================================================
# Usage:
#   .\run_bestfriends_scraper.ps1           # Interactive mode
#   .\run_bestfriends_scraper.ps1 -All      # Scrape everything
#   .\run_bestfriends_scraper.ps1 -All -DB  # Scrape and save to database
# ============================================================================

param(
    [switch]$All,
    [switch]$DB,
    [int]$Batch = 0
)

$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host "Best Friends Network Scraper"
Write-Host "=========================================="

# Navigate to backend directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "backend"

if (-not (Test-Path $BackendDir)) {
    Write-Host "ERROR: backend directory not found at $BackendDir" -ForegroundColor Red
    exit 1
}

Set-Location $BackendDir

# Prefer backend/.venv; fall back to legacy backend/venv; final fallback to `python` on PATH
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = Join-Path $BackendDir "venv\Scripts\python.exe"
}
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

# Build command
$PythonScript = Join-Path $BackendDir "tools\scrape_bestfriends.py"
$Args = @()

if ($All) {
    $Args += "--all"
}

if ($DB) {
    $Args += "--db"
}

if ($Batch -gt 0) {
    $Args += "--batch"
    $Args += $Batch
}

Write-Host "Running: python $PythonScript $($Args -join ' ')"
Write-Host ""

# Run the scraper
if ($Args.Count -gt 0) {
    & $PythonExe $PythonScript @Args
} else {
    & $PythonExe $PythonScript
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Done!"
Write-Host "=========================================="
Write-Host ""
Write-Host "Output files:"
Write-Host "  - backend\data\bf_network_orgs.json"
Write-Host "  - backend\data\bf_network_orgs.csv"
Write-Host ""
