<#
    Aegis — one-time setup on a fresh checkout (Windows / PowerShell).
    Creates Python venvs, installs deps, trains the models, installs Node deps.
    Takes a while the first time (torch download for counterfeit-vision is ~2GB).

    After this finishes, use ./run-all.ps1 to launch everything.

    Requires: Python 3.11+, Node 18+, and `uv` (https://astral.sh/uv) on PATH.
#>

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

function Setup-Py($name, $dir, [switch]$Editable) {
    Write-Host "=== $name ===" -ForegroundColor Cyan
    Push-Location "$root\$dir"
    if (-not (Test-Path ".venv")) { uv venv }
    uv pip install -e ".[dev]"
    Pop-Location
}

# --- Python modules (all use uv + editable install) ---
Setup-Py "Fraud Shield"      "fraud-shield-nlp"
Setup-Py "Counterfeit Vision (downloads torch ~2GB)" "counterfeit-vision"
Setup-Py "Fraud Graph"       "fraud-graph-ml"
Setup-Py "Fusion"            "command-centre\fusion"
Setup-Py "Geospatial"        "command-centre\geospatial"
Setup-Py "Backend"           "command-centre\backend"

# --- train the models (needed before the APIs will serve) ---
Write-Host "=== Training models ===" -ForegroundColor Cyan

Push-Location "$root\fraud-shield-nlp"
.\.venv\Scripts\python -m aegis_fraud_shield.cli train
Pop-Location

Push-Location "$root\counterfeit-vision"
.\.venv\Scripts\python -m aegis_counterfeit.cli generate
.\.venv\Scripts\python -m aegis_counterfeit.cli train
Pop-Location

Push-Location "$root\fraud-graph-ml"
.\.venv\Scripts\fraud-graph demo   # trains + writes output/fraud_graph.json
Pop-Location

# --- Node services ---
Write-Host "=== Node deps ===" -ForegroundColor Cyan
Push-Location "$root\command-centre\gateway";  npm install; Pop-Location
Push-Location "$root\command-centre\frontend"; npm install; Pop-Location

Write-Host ""
Write-Host "Setup complete. Optional: add LLM keys to command-centre\fusion\.env" -ForegroundColor Green
Write-Host "  GROQ_API_KEY=...   (free & fast; template fallback works without it)" -ForegroundColor Gray
Write-Host "Now run:  ./run-all.ps1" -ForegroundColor Yellow
