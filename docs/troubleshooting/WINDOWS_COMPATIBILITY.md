# Windows Compatibility Notes

## Known Issues and Solutions

### 1. Playwright Crawling on Windows

**Issue**: Playwright browser automation fails on Windows when using FastAPI with hot reload.

**Error**: `NotImplementedError` in `asyncio/base_events.py` line 503

**Root Cause**: 
- FastAPI/Uvicorn uses Windows `ProactorEventLoop` for async operations
- Playwright requires `WindowsSelectorEventLoop` for subprocess creation (browser automation)
- These two event loops are incompatible in the same process

**Current Behavior**:
- API server runs successfully ✅
- Health checks work ✅  
- Planning and searching work ✅
- **Crawling fails gracefully** with clear error message ⚠️
- API returns 200 response with fallback answer when no sources available

**Solutions** (choose one):

#### Option 1: Use WSL (Recommended)
```powershell
# Install WSL
wsl --install

# Run in WSL
wsl
cd /mnt/c/Users/Eashwar/Documents/diogenes
python run_api.py
```

#### Option 2: Use Docker
```powershell
docker-compose up
```

#### Option 3: Run Without Hot Reload (Partial Fix)
```powershell
# Use run_api.py instead of src.api.app
python run_api.py
```
Note: This disables hot reload but doesn't fully fix the event loop issue. Crawling may still fail.

#### Option 4: Use Alternative Crawler
Modify `src/services/crawl/crawler.py` to use `requests` + `BeautifulSoup` instead of Playwright:
- Pros: Works on Windows
- Cons: Cannot render JavaScript, less reliable content extraction

### 2. Console Encoding

**Issue**: Windows console (cp1252) doesn't support Unicode emoji characters.

**Error**: `UnicodeEncodeError: 'charmap' codec can't encode character '\u2705'`

**Solution**: Fixed in test scripts by:
1. Setting UTF-8 encoding for stdout/stderr
2. Using ASCII alternatives ([PASS], [FAIL]) instead of emojis

```python
# Fix at top of script
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

## Validation Status

### ✅ Fixed Issues
- Unicode encoding errors in test scripts
- Graceful error handling for Playwright failures  
- Clear warning messages about Windows compatibility
- API returns proper HTTP 200 responses even when crawling fails

### ⚠️ Known Limitations
- Web crawling disabled on Windows with FastAPI
- Search results returned but no content extracted from pages
- Synthesis uses fallback answer when no sources available

### ✅ Working Features
- API server startup and health checks
- Research planning (LLM-based query analysis)
- Multi-query search via SearXNG
- All API endpoints respond correctly
- Mode system (quick/balanced/full/research/deep)
- Streaming endpoints
- Session management

## Testing

### Health Check
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health/" -Method GET
```

### Quick Research Query
```powershell
$body = @{
    query = "What is Python?"
    mode = "quick"
    max_iterations = 1
    streaming = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/research/" -Method POST -Body $body -ContentType "application/json"
```

### Run Test Suite
```powershell
# Start server
Start-Job -ScriptBlock { Set-Location "C:\Users\Eashwar\Documents\diogenes"; python run_api.py }

# Wait for startup
Start-Sleep -Seconds 5

# Run tests
python test_api_endpoints.py

# Stop server
Stop-Job -Name Job1; Remove-Job -Name Job1
```

## Development Recommendations

1. **For Full Functionality**: Use WSL or Linux for development
2. **For Windows Development**: Accept crawling limitation or implement alternative crawler
3. **For Production**: Deploy in Docker/Linux environment
4. **For Testing**: Use provided test scripts with proper encoding

## Log Messages

### Expected Windows Warning
```
WARNING | src.services.crawl.crawler | Windows ProactorEventLoop detected - Playwright crawling will fail. 
For full crawling support on Windows, use WSL, Docker, or switch to WindowsSelectorEventLoop 
(incompatible with FastAPI hot reload).
```

### Expected Crawl Errors
```
ERROR | src.services.crawl.crawler | Playwright not compatible with current Windows event loop
```

These are informational - the API continues to work, just without web page content extraction.
