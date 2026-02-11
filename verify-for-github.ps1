# Quick GitHub Push Script
# Automates pre-push checks for Diogenes

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "Diogenes Pre-Push Verification"
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""

$issues = @()

# Check 1: Search for potential secrets
Write-Host "[1/6] Checking for hardcoded secrets..." -NoNewline
$secretPatterns = "sk-|ghp_|gho_|github_pat_"
$foundSecrets = Get-ChildItem -Recurse -Include "*.py","*.ts","*.tsx","*.js","*.yaml","*.yml" |
    Where-Object { $_.FullName -notmatch "node_modules|_bmad|\.venv|venv" } |
    Select-String -Pattern $secretPatterns -List

if ($foundSecrets) {
    Write-Host " ⚠️  WARNING!" -ForegroundColor Yellow
    Write-Host "      Potential secrets found in:" -ForegroundColor Yellow
    $foundSecrets | ForEach-Object { Write-Host "      - $($_.Path)" -ForegroundColor Yellow }
    $issues += "Potential secrets found"
} else {
    Write-Host " ✅" -ForegroundColor Green
}

# Check 2: Verify .env files not tracked
Write-Host "[2/6] Checking .env files..." -NoNewline
$envFiles = Get-ChildItem -Recurse -Include ".env",".env.local",".env.production" -File |
    Where-Object { $_.Name -notmatch "example" }

if ($envFiles.Count -gt 0) {
    Write-Host " ⚠️  WARNING!" -ForegroundColor Yellow
    Write-Host "      Found .env files (ensure they are gitignored):" -ForegroundColor Yellow
    $envFiles | ForEach-Object { Write-Host "      - $($_.FullName)" -ForegroundColor Yellow }
} else {
    Write-Host " ✅" -ForegroundColor Green
}

# Check 3: Database files
Write-Host "[3/6] Checking for database files..." -NoNewline
$dbFiles = Get-ChildItem -Recurse -Include "*.db","*.sqlite","*.sqlite3" -File
if ($dbFiles.Count -gt 0) {
    Write-Host " ⚠️  Found $($dbFiles.Count) database files" -ForegroundColor Yellow
    Write-Host "      (These should be gitignored)" -ForegroundColor Gray
} else {
    Write-Host " ✅" -ForegroundColor Green
}

# Check 4: node_modules and __pycache__
Write-Host "[4/6] Checking for build artifacts..." -NoNewline
$artifacts = @()
if (Test-Path "frontend/node_modules") { $artifacts += "frontend/node_modules" }
if (Test-Path "node_modules") { $artifacts += "node_modules" }
$pycache = Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Select-Object -First 1

if ($artifacts.Count -gt 0 -or $pycache) {
    Write-Host " ⚠️  Found artifacts" -ForegroundColor Yellow
    Write-Host "      (These should be gitignored)" -ForegroundColor Gray
} else {
    Write-Host " ✅" -ForegroundColor Green
}

# Check 5: Large files
Write-Host "[5/6] Checking for large files (>50MB)..." -NoNewline
$largeFiles = Get-ChildItem -Recurse -File |
    Where-Object { $_.Length -gt 50MB -and $_.FullName -notmatch "node_modules|\.venv|venv" } |
    Select-Object -First 5

if ($largeFiles) {
    Write-Host " ⚠️  WARNING!" -ForegroundColor Yellow
    Write-Host "      Files larger than 50MB found:" -ForegroundColor Yellow
    $largeFiles | ForEach-Object {
        $sizeMB = [math]::Round($_.Length / 1MB, 2)
        Write-Host "      - $($_.Name): ${sizeMB}MB" -ForegroundColor Yellow
    }
    $issues += "Large files found"
} else {
    Write-Host " ✅" -ForegroundColor Green
}

# Check 6: Python syntax check
Write-Host "[6/6] Checking Python syntax..." -NoNewline
try {
    python -m py_compile main.py run_api.py 2>&1 | Out-Null
    Write-Host " ✅" -ForegroundColor Green
} catch {
    Write-Host " ⚠️  Some files may have syntax errors" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 59)

if ($issues.Count -eq 0) {
    Write-Host "Status: ✅ All checks passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Repository is ready to push to GitHub." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor White
    Write-Host "  1. git init" -ForegroundColor Gray
    Write-Host "  2. git add ." -ForegroundColor Gray
    Write-Host "  3. git commit -m `"Initial commit: Diogenes AI Research Assistant`"" -ForegroundColor Gray
    Write-Host "  4. git remote add origin YOUR-GITHUB-URL" -ForegroundColor Gray
    Write-Host "  5. git push -u origin main" -ForegroundColor Gray
} else {
    Write-Host "Status: ⚠️  Warnings detected" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Issues found:" -ForegroundColor Yellow
    $issues | ForEach-Object { Write-Host "  • $_" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "Review the warnings above before pushing." -ForegroundColor Yellow
    Write-Host "See PRE_PUSH_CHECKLIST.md for details." -ForegroundColor Cyan
}

Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""
