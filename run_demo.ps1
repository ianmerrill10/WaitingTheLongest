# Waiting The Longest™ - Demo Launcher
# =============================================================================
# This script launches the full stack for the Waiting The Longest™ demo.
# It starts the FastAPI backend and the Frontend server.
# =============================================================================

Write-Host "Starting Waiting The Longest™ Demo..." -ForegroundColor Cyan

# 2. Define Paths
$ScriptDir = $PSScriptRoot
$BackendDir = Join-Path $ScriptDir "backend"
$VenvDir = Join-Path $BackendDir ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

$DemoUrl = "http://127.0.0.1:8000/demo"
$HealthUrl = "http://127.0.0.1:8000/health"

# 1. Check for backend venv python
if (-not (Test-Path $PythonExe)) {
    Write-Error "Backend virtual environment not found at $PythonExe"
    Write-Host "Create it under backend/.venv and install requirements first." -ForegroundColor Yellow
    exit 1
}

# Quick check: if the API is already running, just open the demo.
$ServerAlreadyRunning = $false
try {
    $ProgressPreference = 'SilentlyContinue'
    $resp = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 2
    if ($null -ne $resp) {
        $ServerAlreadyRunning = $true
    }
} catch {
    $ServerAlreadyRunning = $false
}

# 3. Generate Demo Data (idempotent; safe to run even if server is running)
Write-Host "Generating demo data..." -ForegroundColor Green
Set-Location $BackendDir
& $PythonExe tools\generate_demo_data.py

# 4. Start Backend Server (if not already running)
$BackendProc = $null
if (-not $ServerAlreadyRunning) {
    Write-Host "Starting Backend Server (FastAPI) on port 8000..." -ForegroundColor Green
    $BackendProc = Start-Process -FilePath $PythonExe -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -PassThru

    Write-Host "Waiting for server to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 4

    # Confirm it started; if not, don't hang.
    try {
        $ProgressPreference = 'SilentlyContinue'
        $null = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 4
    } catch {
        Write-Error "Backend did not start or port 8000 is blocked. If another process is using it, stop that process and retry."
        if ($BackendProc) {
            try { Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue } catch {}
        }
        exit 1
    }
} else {
    Write-Host "Backend already running; reusing existing server." -ForegroundColor Yellow
}

# 5. Open in Browser
Write-Host "Opening demo at $DemoUrl" -ForegroundColor Cyan
Start-Process $DemoUrl

# 6. Keep script running only if we started the backend
if ($BackendProc) {
    Write-Host "Demo is running!" -ForegroundColor Green
    Write-Host "Press any key to stop the backend and exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

    Write-Host "Stopping backend..." -ForegroundColor Yellow
    try { Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue } catch {}
    Write-Host "Demo stopped." -ForegroundColor Cyan
} else {
    Write-Host "Demo opened. Backend left running." -ForegroundColor Green
}
