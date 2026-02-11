# Windows Crawling Limitation - ROOT CAUSE ANALYSIS

## The Problem

Playwright web crawling fails on Windows with FastAPI due to a fundamental incompatibility:

```
NotImplementedError: asyncio.create_subprocess_exec not supported on Windows event loops
```

## Root Cause

1. **Playwright** requires launching browser processes using `asyncio.create_subprocess_exec()`
2. **Windows ProactorEventLoop** (FastAPI default) doesn't properly support subprocess creation
3. **Windows SelectorEventLoop** also raises `NotImplementedError` for subprocess operations
4. This is a **known limitation** of Python's asyncio on Windows

## What We Tried

### ❌ Attempt 1: Direct Event Loop Fix
- Added `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`
- **Failed**: SelectorEventLoop also doesn't support subprocesses

### ❌ Attempt 2: Thread Pool Workaround
- Created separate threads with WindowsSelectorEventLoop for Playwright
- **Failed**: Same subprocess limitation exists in threads

## Solutions

###  ✅ Option 1: Use WSL or Docker (RECOMMENDED for Production)
```powershell
# Install WSL
wsl --install

# Run in WSL
wsl
cd /mnt/c/Users/Eashwar/Documents/diogenes
python run_api.py
```

### ✅ Option 2: Fallback to Simple HTTP Crawler (Quick Fix)
Use `requests` + `BeautifulSoup` instead of Playwright on Windows:
- ✅ Works on Windows
- ✅ No subprocess needed
- ❌ Can't handle JavaScript-heavy sites
- ❌ May be blocked by some sites

### ✅ Option 3: Search-Only Mode
Disable crawling entirely and rely only on search result snippets:
- Fast
- Works everywhere
- Limited content depth

## Current Status

🔧 **Implementing Option 2**: Fallback HTTP crawler for Windows development

This allows:
- ✅ Development and testing on Windows
- ✅ Full functionality on Linux/WSL/Docker
- ✅ Graceful degradation on Windows

## Recommendation

For **production deployment**, use:
- Docker container (Linux-based)
- OR WSL environment
- OR Linux server

This issue ONLY affects Windows native Python. Linux/Mac work perfectly.
