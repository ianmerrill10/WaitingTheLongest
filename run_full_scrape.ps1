# ============================================================================
# NATIONWIDE RESCUE REGISTRY - Complete Build Pipeline
# ============================================================================
# Builds complete shelter/rescue database from ALL sources:
#   1. Local data files (NJ, RI, National Registry, AKC) ~800+ orgs
#   2. Best Friends Network (3 phases) ~5,800 orgs
#   3. Adopt-a-Pet directory ~10,000+ orgs
#   4. Deduplication
#   5. Split by state
#
# Usage:
#   .\run_full_scrape.ps1              # Run EVERYTHING
#   .\run_full_scrape.ps1 -DB          # Run everything + save to database
#   .\run_full_scrape.ps1 -LocalOnly   # Just local data files
#   .\run_full_scrape.ps1 -BFOnly      # Just Best Friends (3 phases)
#   .\run_full_scrape.ps1 -AdoptOnly   # Just Adopt-a-Pet
#   .\run_full_scrape.ps1 -Dedupe      # Just deduplication
# ============================================================================

param(
    [switch]$DB,
    [switch]$LocalOnly,
    [switch]$BFOnly,
    [switch]$AdoptOnly,
    [switch]$Dedupe
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  NATIONWIDE RESCUE REGISTRY BUILDER" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to backend directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "backend"

if (-not (Test-Path $BackendDir)) {
    Write-Host "ERROR: backend directory not found" -ForegroundColor Red
    exit 1
}

Set-Location $BackendDir

# Activate venv if exists
$VenvPath = Join-Path $BackendDir "venv\Scripts\Activate.ps1"
if (Test-Path $VenvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Gray
    & $VenvPath
}

$StartTime = Get-Date
$RunAll = -not ($LocalOnly -or $BFOnly -or $AdoptOnly -or $Dedupe)

# ============================================================================
# SOURCE 1: LOCAL DATA FILES
# ============================================================================
if ($RunAll -or $LocalOnly) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "  SOURCE 1: Local Data Files" -ForegroundColor Yellow
    Write-Host "  (NJ, RI, National Registry, AKC ~800+ orgs)" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host ""

    python tools/ingest_all_local.py

    Write-Host ""
    Write-Host "Local data ingestion complete!" -ForegroundColor Green
}

# ============================================================================
# SOURCE 2: BEST FRIENDS NETWORK (3 Phases)
# ============================================================================
if ($RunAll -or $BFOnly) {
    # Phase 1: Scrape directory
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "  SOURCE 2a: Best Friends Directory" -ForegroundColor Yellow
    Write-Host "  (~5,800 orgs, takes 15-20 minutes)" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host ""

    $Args1 = @("tools/scrape_bestfriends.py", "--all")
    if ($DB) { $Args1 += "--db" }
    python @Args1

    # Phase 2: Enrich from BF profiles
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "  SOURCE 2b: BF Profile Enrichment" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host ""

    $Args2 = @("tools/enrich_bestfriends.py", "--all")
    if ($DB) { $Args2 += "--db" }
    python @Args2

    # Phase 3: Deep website enrichment
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "  SOURCE 2c: Website Deep Enrichment" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host ""

    $Args3 = @("tools/enrich_websites.py", "--all")
    if ($DB) { $Args3 += "--db" }
    python @Args3

    Write-Host ""
    Write-Host "Best Friends scrape complete!" -ForegroundColor Green
}

# ============================================================================
# SOURCE 3: ADOPT-A-PET DIRECTORY
# ============================================================================
if ($RunAll -or $AdoptOnly) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "  SOURCE 3: Adopt-a-Pet Directory" -ForegroundColor Yellow
    Write-Host "  (~10,000+ orgs across all states)" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host ""

    $ArgsAdopt = @("tools/scrape_adoptapet.py", "--all")
    if ($DB) { $ArgsAdopt += "--db" }
    python @ArgsAdopt

    Write-Host ""
    Write-Host "Adopt-a-Pet scrape complete!" -ForegroundColor Green
}

# ============================================================================
# DEDUPLICATION
# ============================================================================
if ($RunAll -or $Dedupe) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "  DEDUPLICATION" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host ""

    if ($DB) {
        python tools/deduplicate_shelters.py --merge
    } else {
        python tools/deduplicate_shelters.py
    }

    Write-Host ""
    Write-Host "Deduplication complete!" -ForegroundColor Green
}

# ============================================================================
# SPLIT BY STATE
# ============================================================================
if ($RunAll) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "  SPLITTING BY STATE" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host ""

    python tools/split_by_state.py

    Write-Host ""
    Write-Host "Split complete!" -ForegroundColor Green
}

# ============================================================================
# SUMMARY
# ============================================================================
$EndTime = Get-Date
$Duration = $EndTime - $StartTime

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  BUILD COMPLETE!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Duration: $($Duration.ToString('hh\:mm\:ss'))" -ForegroundColor Gray
Write-Host ""
Write-Host "Data Sources:" -ForegroundColor White
Write-Host "  1. Local files (NJ, RI, National, AKC)" -ForegroundColor Gray
Write-Host "  2. Best Friends Network (~5,800 orgs)" -ForegroundColor Gray
Write-Host "  3. Adopt-a-Pet (~10,000+ orgs)" -ForegroundColor Gray
Write-Host ""
Write-Host "Output files in backend/data/:" -ForegroundColor White
Write-Host "  - bf_network_*.json        (Best Friends data)" -ForegroundColor Gray
Write-Host "  - adoptapet_shelters.json  (Adopt-a-Pet data)" -ForegroundColor Gray
Write-Host "  - by_state/shelters_*.csv  (Per-state CSVs)" -ForegroundColor Gray
Write-Host ""
if ($DB) {
    Write-Host "Database updated with all sources!" -ForegroundColor Green
    Write-Host ""
}
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
