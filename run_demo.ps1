# Waiting The Longest™ - Demo Launcher
# =============================================================================
# This script launches the full stack for the Waiting The Longest™ demo.
# It starts the FastAPI backend and the Frontend server.
# =============================================================================

Write-Host "Starting Waiting The Longest™ Demo..." -ForegroundColor Cyan

# 1. Check for Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}

# 2. Define Paths
$ScriptDir = $PSScriptRoot
$BackendDir = Join-Path $ScriptDir "backend"
$FrontendDir = Join-Path $ScriptDir "frontend"
$VenvDir = Join-Path $BackendDir "venv"

# 3. Activate Virtual Environment
$VenvActivate = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    . $VenvActivate
} else {
    Write-Warning "Virtual environment not found at $VenvDir. Attempting to use system python."
}

# 4. Start Backend Server (Background Job)
Write-Host "Starting Backend Server (FastAPI) on port 8000..." -ForegroundColor Green
$BackendJob = Start-Job -ScriptBlock {
    param($Dir)
    Set-Location $Dir
    # Ensure backend directory is in PYTHONPATH
    $env:PYTHONPATH = $Dir
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} -ArgumentList $BackendDir

# 5. Start Frontend Server (Background Job)
Write-Host "Starting Frontend Server on port 3000..." -ForegroundColor Green
$FrontendJob = Start-Job -ScriptBlock {
    param($Dir)
    Set-Location $Dir
    python -m http.server 3000
} -ArgumentList $FrontendDir

# 6. Wait for servers to spin up
Write-Host "Waiting for servers to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 7. Open in Browser
$DemoUrl = "http://localhost:3000/demo.html"
Write-Host "Opening demo at $DemoUrl" -ForegroundColor Cyan
Start-Process $DemoUrl

# 8. Keep script running to maintain jobs
Write-Host "Demo is running!" -ForegroundColor Green
Write-Host "Press any key to stop servers and exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# 9. Cleanup
Write-Host "Stopping servers..." -ForegroundColor Yellow
Stop-Job $BackendJob
Remove-Job $BackendJob
Stop-Job $FrontendJob
Remove-Job $FrontendJob
Write-Host "Demo stopped." -ForegroundColor Cyan
