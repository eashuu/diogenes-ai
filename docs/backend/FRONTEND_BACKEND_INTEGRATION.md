# Diogenes Frontend + Backend Integration

This guide explains how to run the connected Diogenes frontend and backend.

## Prerequisites

- Python 3.10+ (for backend)
- Node.js 18+ (for frontend)
- Running SearXNG instance (for search functionality)

## Backend Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   - Copy `config/development.yaml` and customize if needed
   - Ensure SearXNG is running (see docker-compose.yml)

3. **Start the backend API:**
   ```bash
   python run_api.py
   ```
   
   The API will run on `http://localhost:8000`

## Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment:**
   - Check `.env.local` file (already configured to connect to `http://localhost:8000/api`)

4. **Start the development server:**
   ```bash
   npm run dev
   ```
   
   The frontend will run on `http://localhost:5173` (or the next available port)

## How It Works

### Backend (Diogenes API)
- **Research Endpoint:** `POST /api/v1/research/`
- **Streaming Endpoint:** `POST /api/v1/research/stream`
- **Health Check:** `GET /api/v1/health/`

The backend uses:
- Multi-agent research orchestration
- SearXNG for web search
- Playwright for web crawling
- LLMs for synthesis and verification

### Frontend (React + TypeScript)
- Built with React 19, TypeScript, Vite
- Uses Tailwind CSS for styling
- Connects to backend via REST API and Server-Sent Events (SSE)
- Supports three research modes: Quick, Balanced, Deep
- Six research profiles: General, Academic, Technical, News, Medical, Legal

### Key Features

1. **Streaming Research:** Real-time updates as research progresses
2. **Source Citations:** Inline citations with source panel
3. **Research Modes:**
   - Quick: Fast, concise answers (~30s)
   - Balanced: Standard research (~1m)
   - Deep: Comprehensive analysis (~3m)
4. **Research Profiles:** Tailored output for different domains
5. **Session History:** Local storage of past research sessions

## API Integration Details

The frontend communicates with the backend through:

### API Service (`lib/api-service.ts`)
- `DiogenesAPIService` class wraps all API calls
- Handles streaming SSE connections
- Converts backend responses to frontend types

### Type Definitions (`lib/api-types.ts`)
- TypeScript interfaces for all API requests/responses
- SSE event type definitions

### Demo Component (`demo.tsx`)
- `runDiogenesResearch()` function orchestrates API calls
- Handles streaming events and UI updates
- Manages chat sessions and sources

## Troubleshooting

### Backend Issues
- **Port already in use:** Change port in `run_api.py`
- **SearXNG connection failed:** Ensure Docker container is running
- **LLM errors:** Check your LLM configuration in `config/development.yaml`

### Frontend Issues
- **API connection failed:** Verify backend is running on port 8000
- **Type errors:** Run `npm install` to ensure all dependencies are installed
- **Build errors:** Clear node_modules and reinstall: `rm -rf node_modules && npm install`

## Development Tips

### Backend Development
```bash
# Run with auto-reload
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
# Run with HMR (Hot Module Replacement)
npm run dev
```

### Testing the Connection
1. Start backend: `python run_api.py`
2. Check health: `curl http://localhost:8000/api/v1/health/`
3. Start frontend: `cd frontend && npm run dev`
4. Open browser: `http://localhost:5173`
5. Submit a test query and verify streaming works

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Frontend      │         │   Backend API    │         │  SearXNG    │
│   (React/Vite)  │ ◄─SSE─► │   (FastAPI)      │ ◄────► │  (Docker)   │
│   Port 5173     │         │   Port 8000      │         │  Port 8080  │
└─────────────────┘         └──────────────────┘         └─────────────┘
         │                           │
         │                           │
         │                           ▼
         │                  ┌──────────────────┐
         │                  │   Multi-Agent    │
         │                  │   Orchestrator   │
         │                  └──────────────────┘
         │                           │
         │                           ├─► Search Agent
         │                           ├─► Crawl Agent
         │                           ├─► Synthesis Agent
         │                           └─► Verification Agent
         │
         └──► localStorage (sessions)
```

## Next Steps

- Add authentication/user management
- Implement conversation memory
- Add export functionality for research reports
- Deploy to production (see WINDOWS_COMPATIBILITY.md for Windows deployment notes)
