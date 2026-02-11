# Diogenes Startup Script for Windows
# This script starts both the backend and frontend servers

Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "Diogenes - Research Assistant Startup"
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""

# Check for SearXNG (REQUIRED!)
Write-Host "[1/5] Checking for SearXNG (REQUIRED)..." -ForegroundColor Cyan
$searxngUrl = "http://localhost:8080/"
try {
    $response = Invoke-WebRequest -Uri $searxngUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "      ✅ SearXNG is running on port 8080!" -ForegroundColor Green
} catch {
    Write-Host "      ❌ SearXNG is NOT running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "      SearXNG is REQUIRED for Diogenes to work!" -ForegroundColor Yellow
    Write-Host "      Please start it with:" -ForegroundColor Yellow
    Write-Host "          docker-compose up -d searxng" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "      Or use docker directly:" -ForegroundColor Yellow
    Write-Host "          docker run -d -p 8080:8080 searxng/searxng:latest" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}
Write-Host ""

# Configurable backend port
$backendPort = 8000
$backendHealthUrl = "http://localhost:$backendPort/health/"

Write-Host "[2/5] Checking if backend is already running..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri $backendHealthUrl -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "      Backend is already running!" -ForegroundColor Green
    $backendRunning = $true
} catch {
    Write-Host "      Backend is not running" -ForegroundColor Yellow
    if ($_.Exception.Response -ne $null) {
        Write-Host ("      Health check error: " + $_.Exception.Response.StatusCode.value__) -ForegroundColor Red
    } elseif ($_.Exception.Message) {
        Write-Host ("      Health check error: " + $_.Exception.Message) -ForegroundColor Red
    }
    $backendRunning = $false
}


# Start backend if not running
if (-not $backendRunning) {
    Write-Host ""
    Write-Host "[3/5] Starting backend API server..." -ForegroundColor Cyan

    # Check for python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "      Python is not installed or not in PATH!" -ForegroundColor Red
        exit 1
    }

    # Start backend in new window, set working directory
    Start-Process powershell -WorkingDirectory $PSScriptRoot -ArgumentList @(
        "-NoExit",
        "-Command",
        "Write-Host 'Starting Diogenes Backend...' -ForegroundColor Green; python run_api.py"
    )

    # Wait a moment for process to start
    Start-Sleep -Seconds 2
    Write-Host "      Waiting for backend to start..." -ForegroundColor Yellow
    $maxAttempts = 30
    $attempt = 0
    $backendReady = $false
    $spinner = @('|','/','-','\\')
    $spinIndex = 0
    while ($attempt -lt $maxAttempts -and -not $backendReady) {
        Start-Sleep -Seconds 1
        $attempt++
        try {
            $response = Invoke-RestMethod -Uri $backendHealthUrl -Method GET -TimeoutSec 5 -ErrorAction Stop
            $backendReady = $true
            Write-Host "`r      Backend is ready!           " -ForegroundColor Green
        } catch {
            Write-Host ("`r      Waiting... " + $spinner[$spinIndex]) -NoNewline
            $spinIndex = ($spinIndex + 1) % $spinner.Length
            if ($attempt -eq $maxAttempts) {
                if ($_.Exception.Response -ne $null) {
                    Write-Host ("`n      Health check error: " + $_.Exception.Response.StatusCode.value__) -ForegroundColor Red
                } elseif ($_.Exception.Message) {
                    Write-Host ("`n      Health check error: " + $_.Exception.Message) -ForegroundColor Red
                }
            }
        }
    }
    Write-Host ""
    if (-not $backendReady) {
        Write-Host "      Backend failed to start after 30 seconds" -ForegroundColor Red
        Write-Host "      Please check the backend window for errors" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "[3/5] Backend already running, skipping..." -ForegroundColor Green
    Write-Host ""
}


# Start frontend
Write-Host "[4/5] Starting frontend development server..." -ForegroundColor Cyan

# Check if node_modules exists
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "      node_modules not found. Running npm install..." -ForegroundColor Yellow
    Push-Location frontend
    npm install
    Pop-Location
}

# Start frontend in new window, set working directory
Start-Process powershell -WorkingDirectory (Join-Path $PSScriptRoot 'frontend') -ArgumentList @(
    "-NoExit",
    "-Command",
    "Write-Host 'Starting Diogenes Frontend...' -ForegroundColor Green; npm run dev"
)

Write-Host "      Frontend server starting..." -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "[5/5] Startup complete!" -ForegroundColor Cyan
Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "Services:"
Write-Host "  SearXNG:      http://localhost:8080" -ForegroundColor White
Write-Host "  Backend API:  http://localhost:$backendPort" -ForegroundColor White
Write-Host "  Frontend:     http://localhost:5173" -ForegroundColor White
Write-Host "  API Docs:     http://localhost:$backendPort/docs" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop the services"
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""
Write-Host "Opening browser in 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Open browser
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "Diogenes is running! Happy researching!" -ForegroundColor Green
