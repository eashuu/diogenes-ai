# Build and Test SearXNG Docker Image
# Quick script to build and verify SearXNG is working

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "Building Diogenes SearXNG Docker Image"
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""

# Check if Docker is running
Write-Host "[1/4] Checking Docker..." -NoNewline
try {
    docker version | Out-Null
    Write-Host " ✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host " ❌ Docker is not running!" -ForegroundColor Red
    Write-Host "      Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# Build SearXNG image
Write-Host "[2/4] Building SearXNG image (this may take 2-3 minutes)..." -ForegroundColor Cyan
try {
    docker-compose build searxng
    Write-Host "      ✅ Build successful!" -ForegroundColor Green
} catch {
    Write-Host "      ❌ Build failed!" -ForegroundColor Red
    Write-Host "      Check the error messages above" -ForegroundColor Yellow
    exit 1
}

# Start SearXNG container
Write-Host "[3/4] Starting SearXNG container..." -ForegroundColor Cyan
try {
    docker-compose up -d searxng
    Write-Host "      ✅ Container started!" -ForegroundColor Green
} catch {
    Write-Host "      ❌ Failed to start container!" -ForegroundColor Red
    exit 1
}

# Wait for SearXNG to be ready
Write-Host "[4/4] Waiting for SearXNG to be ready..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

$maxAttempts = 10
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        $ready = $true
        Write-Host "      ✅ SearXNG is ready and responding!" -ForegroundColor Green
    } catch {
        $attempt++
        if ($attempt -lt $maxAttempts) {
            Write-Host "      Waiting... (attempt $attempt/$maxAttempts)" -ForegroundColor Yellow
            Start-Sleep -Seconds 2
        } else {
            Write-Host "      ⚠️  SearXNG started but not responding yet" -ForegroundColor Yellow
            Write-Host "      Try: curl http://localhost:8080/" -ForegroundColor Gray
        }
    }
}

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 59)

if ($ready) {
    Write-Host "Success! SearXNG is running on http://localhost:8080" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Start Ollama: ollama serve" -ForegroundColor White
    Write-Host "  2. Start Backend: python run_api.py" -ForegroundColor White
    Write-Host "  3. Start Frontend: cd frontend && npm run dev" -ForegroundColor White
} else {
    Write-Host "SearXNG container started but may still be initializing" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Check status with:" -ForegroundColor Cyan
    Write-Host "  docker logs diogenes-searxng" -ForegroundColor White
    Write-Host "  curl http://localhost:8080/" -ForegroundColor White
}

Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""
