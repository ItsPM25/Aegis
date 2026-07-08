<#
    Aegis — start all 6 services locally (Windows / PowerShell).

    Usage:
        ./run-all.ps1          # start everything in separate windows
        ./run-all.ps1 -Stop    # stop everything (kills the service ports)

    Ports:  8001 Fraud Shield · 8002 Counterfeit Vision · 8003 Fraud Graph
            8000 Backend · 4000 Gateway · 3000 Dashboard

    Prereqs (one-time): each Python module has a .venv, models are trained,
    and `npm install` has been run in gateway/ and frontend/.
    Run ./setup.ps1 first if you're on a fresh checkout.
#>

param([switch]$Stop)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$ports = 8000, 8001, 8002, 8003, 4000, 3000

function Stop-Ports {
    foreach ($p in $ports) {
        Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue |
            Select-Object -Expand OwningProcess -Unique |
            ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    }
    Write-Host "Stopped services on ports: $($ports -join ', ')" -ForegroundColor Yellow
}

if ($Stop) { Stop-Ports; return }

# Start a service in its own PowerShell window so logs stay readable.
function Start-Service($title, $dir, $cmd) {
    $full = "cd '$dir'; Write-Host '=== $title ===' -ForegroundColor Cyan; $cmd"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $full
    Write-Host "  started $title" -ForegroundColor Green
}

Write-Host "Starting Aegis (6 services)..." -ForegroundColor Cyan

# --- detection modules ---
Start-Service "Fraud Shield :8001" "$root\fraud-shield-nlp" `
    ".\.venv\Scripts\uvicorn aegis_fraud_shield.api:app --app-dir src --port 8001"

Start-Service "Counterfeit Vision :8002" "$root\counterfeit-vision" `
    ".\.venv\Scripts\uvicorn aegis_counterfeit.api:app --app-dir src --port 8002"

Start-Service "Fraud Graph :8003" "$root\fraud-graph-ml" `
    ".\.venv\Scripts\fraud-graph serve"

# --- command centre ---
Start-Service "Backend :8000" "$root\command-centre\backend" `
    ".\.venv\Scripts\uvicorn aegis_command.api:app --app-dir src --port 8000"

Start-Service "Gateway :4000" "$root\command-centre\gateway" `
    "npm start"

Start-Service "Dashboard :3000" "$root\command-centre\frontend" `
    "npm run dev"

Write-Host ""
Write-Host "All services launching in separate windows." -ForegroundColor Green
Write-Host "Dashboard:  http://localhost:3000" -ForegroundColor White
Write-Host "Fraud Shield demo UI:  http://localhost:8001/" -ForegroundColor White
Write-Host "Counterfeit demo UI:   http://localhost:8002/" -ForegroundColor White
Write-Host ""
Write-Host "Stop everything:  ./run-all.ps1 -Stop" -ForegroundColor Yellow
