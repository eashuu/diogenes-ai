# Frontend-Backend Integration Summary

## Overview
Successfully connected the Diogenes frontend (React/TypeScript) with the Diogenes backend (FastAPI/Python) to create a fully functional AI-powered research assistant.

## Changes Made

### 1. Environment Configuration
**File:** [frontend/.env.local](frontend/.env.local)
- Added `VITE_API_URL` pointing to `http://localhost:8000/api`
- Kept `VITE_GEMINI_API_KEY` as placeholder for future use

### 2. TypeScript Type Definitions
**File:** [frontend/lib/api-types.ts](frontend/lib/api-types.ts) *(NEW)*
- Defined all backend API request/response types
- SSE (Server-Sent Events) event types
- Source, ResearchResponse, ResearchRequest interfaces
- Fully typed integration for type safety

### 3. API Service Module
**File:** [frontend/lib/api-service.ts](frontend/lib/api-service.ts) *(NEW)*
- Created `DiogenesAPIService` class
- Implements REST API calls (`research()`)
- Implements SSE streaming (`researchStream()`)
- Handles event parsing and error handling
- Singleton instance `apiService` exported for use

### 4. Frontend Application Updates
**File:** [frontend/demo.tsx](frontend/demo.tsx)
- **Removed:** Google Gemini API integration
- **Added:** Diogenes backend API integration via `apiService`
- **Updated Types:**
  - Changed `GroundingChunk` to `Source` to match backend
  - Removed Gemini-specific settings (model, grounding, provider)
  - Updated `UserSettings` interface
- **New Function:** `runDiogenesResearch()` replaces `runGeminiGeneration()`
  - Uses backend streaming API
  - Handles SSE events (status, source, synthesis, complete, error)
  - Real-time UI updates during research
- **Updated Components:**
  - `SidebarSourceCard` now uses `Source` type
  - `CitationChip` updated for new source format
  - Sources panel rendering updated

### 5. Documentation
**File:** [FRONTEND_BACKEND_INTEGRATION.md](FRONTEND_BACKEND_INTEGRATION.md) *(NEW)*
- Complete setup guide for both frontend and backend
- Architecture diagram
- Troubleshooting section
- Development tips
- API endpoint documentation

### 6. Testing & Utilities
**File:** [scripts/test_integration.py](scripts/test_integration.py) *(NEW)*
- Health check test
- Research API test
- CORS configuration test
- Automated validation script

**File:** [start-diogenes.ps1](start-diogenes.ps1) *(NEW)*
- PowerShell startup script for Windows
- Automatically starts backend and frontend
- Health checks and status monitoring
- Opens browser when ready

## Architecture Flow

```
User Query → Frontend (React)
    ↓
API Service (TypeScript)
    ↓
Backend API (FastAPI) → Multi-Agent Orchestrator
    ↓                       ↓
SSE Stream              Search → Crawl → Synthesize → Verify
    ↓                       ↓
Frontend Updates        Sources Collected
    ↓
Real-time Display with Citations
```

## Key Features Preserved

✓ **Three Research Modes:** Quick, Balanced, Deep  
✓ **Six Research Profiles:** General, Academic, Technical, News, Medical, Legal  
✓ **Real-time Streaming:** SSE for progress updates  
✓ **Source Citations:** Inline citations with clickable references  
✓ **Source Panel:** View all sources with quality scores  
✓ **Session History:** Local storage of past conversations  
✓ **Theme Support:** Light, Dark, Diogenes themes  
✓ **Responsive UI:** Works on desktop and mobile  

## New Backend Integration Features

✓ **Multi-Agent Research:** Specialized agents for different tasks  
✓ **Claim Verification:** Automatic fact-checking  
✓ **Reliability Scoring:** Source quality assessment  
✓ **Profile Auto-Detection:** Intelligent query categorization  
✓ **Web Crawling:** Deep content extraction from sources  
✓ **SearXNG Integration:** Privacy-focused multi-search  

## How to Run

### Option 1: Using the startup script (Recommended)
```powershell
.\start-diogenes.ps1
```

### Option 2: Manual startup

**Terminal 1 - Backend:**
```bash
python run_api.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install  # first time only
npm run dev
```

### Option 3: Test integration first
```bash
python scripts/test_integration.py
```

## API Endpoints Used

### Backend Endpoints
- `POST /api/v1/research/` - Blocking research query
- `POST /api/v1/research/stream` - Streaming research with SSE
- `GET /api/v1/health/` - Health check

### Frontend Calls
```typescript
// Non-streaming
const response = await apiService.research({
  query: "What is quantum computing?",
  mode: "balanced",
  profile: "general"
});

// Streaming
for await (const event of apiService.researchStream({
  query: "Explain AI",
  mode: "quick"
})) {
  if (event.type === 'synthesis') {
    console.log(event.data.content);
  }
}
```

## Testing Checklist

- [x] Backend health endpoint accessible
- [x] Frontend can connect to backend
- [x] Streaming events work correctly
- [x] Sources display properly
- [x] Citations render inline
- [x] Research modes (quick/balanced/deep) work
- [x] Research profiles apply correctly
- [x] Session history saves/loads
- [x] Regenerate function works
- [x] Theme switching works

## Known Limitations

1. **No Authentication:** Currently open access (add auth for production)
2. **Local Storage Only:** Sessions stored in browser (add backend persistence)
3. **Single User:** No multi-user support yet
4. **No Export:** Research reports can't be exported yet (PDF/MD planned)

## Next Steps

### Short Term
- [ ] Add loading states for better UX
- [ ] Implement error retry logic
- [ ] Add request cancellation support
- [ ] Improve mobile responsiveness

### Medium Term
- [ ] Add user authentication
- [ ] Backend session persistence
- [ ] Export to PDF/Markdown
- [ ] Share research sessions

### Long Term
- [ ] Real-time collaboration
- [ ] Advanced analytics dashboard
- [ ] Custom research profiles
- [ ] Plugin system for extensions

## Troubleshooting

### "Cannot connect to backend"
- Verify backend is running: `curl http://localhost:8000/api/v1/health/`
- Check firewall settings
- Ensure port 8000 is not blocked

### "Streaming not working"
- Check browser console for SSE errors
- Verify CORS headers in backend response
- Try non-streaming endpoint first

### "No sources showing"
- Check backend logs for crawl errors
- Verify SearXNG is running
- Check network connectivity

## Performance Notes

- **Quick Mode:** ~30 seconds, 3-5 sources
- **Balanced Mode:** ~60 seconds, 5-8 sources
- **Deep Mode:** ~180 seconds, 10-15 sources

Actual times vary based on:
- Query complexity
- Network speed
- LLM response time
- Number of sources to crawl

## Credits

- Frontend: React 19, TypeScript, Vite, Tailwind CSS
- Backend: FastAPI, Python 3.10+, LangGraph
- Search: SearXNG (privacy-focused meta-search)
- UI Components: shadcn/ui, Framer Motion
- Icons: Lucide React

---

**Status:** ✅ Fully Integrated and Tested  
**Version:** v2.0  
**Last Updated:** 2026-02-01
