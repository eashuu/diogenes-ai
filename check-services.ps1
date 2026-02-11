# Diogenes Service Health Check
# Quick script to verify all required services are running

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "Diogenes Service Health Check"
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""

$allGood = $true

# Check SearXNG (REQUIRED)
Write-Host "[1/4] SearXNG (REQUIRED)..." -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host " ✅ Running" -ForegroundColor Green
} catch {
    Write-Host " ❌ NOT RUNNING" -ForegroundColor Red
    Write-Host "      Start with: docker-compose up -d searxng" -ForegroundColor Yellow
    $allGood = $false
}

# Check Ollama (Optional but recommended)
Write-Host "[2/4] Ollama (LLM)..." -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host " ✅ Running" -ForegroundColor Green
} catch {
    Write-Host " ⚠️  Not running (optional)" -ForegroundColor Yellow
    Write-Host "      Start with: ollama serve" -ForegroundColor Gray
}

# Check Backend API
Write-Host "[3/4] Backend API..." -NoNewline
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health/" -TimeoutSec 3 -ErrorAction Stop
    if ($response.status -eq "healthy") {
        Write-Host " ✅ Running (healthy)" -ForegroundColor Green
    } else {
        Write-Host " ⚠️  Running but unhealthy" -ForegroundColor Yellow
        Write-Host "      Status: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
    }
} catch {
    Write-Host " ❌ Not running" -ForegroundColor Red
    Write-Host "      Start with: python run_api.py" -ForegroundColor Yellow
    $allGood = $false
}

# Check Frontend
Write-Host "[4/4] Frontend..." -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host " ✅ Running" -ForegroundColor Green
} catch {
    # Try alternative port 5173 (Vite default)
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5173/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-Host " ✅ Running (port 5173)" -ForegroundColor Green
    } catch {
        Write-Host " ❌ Not running" -ForegroundColor Red
        Write-Host "      Start with: cd frontend && npm run dev" -ForegroundColor Yellow
        $allGood = $false
    }
}

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 59)

if ($allGood) {
    Write-Host "Status: All required services are running! ✅" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can access Diogenes at:" -ForegroundColor Cyan
    Write-Host "  • Frontend:   http://localhost:3000" -ForegroundColor White
    Write-Host "  • Backend:    http://localhost:8000" -ForegroundColor White
    Write-Host "  • API Docs:   http://localhost:8000/docs" -ForegroundColor White
} else {
    Write-Host "Status: Some required services are not running! ❌" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start the missing services above." -ForegroundColor Yellow
}

Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""
