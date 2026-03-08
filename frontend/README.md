# Diogenes Frontend

React 19 + TypeScript single-page app for the Diogenes AI Research Assistant.

## Quick Start

```bash
npm install
npm run dev        # → http://localhost:3000
```

The frontend expects the backend API at `http://localhost:8000`. Set `VITE_API_URL` in `.env.local` to override.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server (port 3000) |
| `npm run build` | Production build → `dist/` |
| `npm run preview` | Preview production build |
| `npm run typecheck` | TypeScript type checking |

## Tech Stack

- **React 19** with TypeScript
- **Vite** — build tool and dev server
- **Tailwind CSS 3.4** — utility-first styling
- **Framer Motion 11** — animations
- **lucide-react** — icon library
- **react-markdown** — Markdown rendering with syntax highlighting

## Component Architecture

All components live in `components/`:

| Component | Purpose |
|-----------|---------|
| `ChatWindow.tsx` | Main chat view — message list, scroll, streaming |
| `MessageBox.tsx` | Single message bubble — user or AI with citations |
| `MessageInput.tsx` | Input bar — text, file upload, focus mode selector |
| `MessageSources.tsx` | Citation sidebar — source cards with favicons |
| `Sidebar.tsx` | Session list, navigation, new chat |
| `Navbar.tsx` | Top bar — title, hamburger menu (mobile) |
| `EmptyChat.tsx` | Landing page — suggestions, weather widget |
| `SettingsModal.tsx` | 4-tab settings (General, Intelligence, Appearance, Data) |
| `DiscoverPage.tsx` | Trending articles by category with "Research this" |
| `LibraryPage.tsx` | Search, filter, sort, bulk delete, export sessions |
| `ThinkBox.tsx` | Chain-of-thought display, parses `<think>` tags |
| `ResearchSteps.tsx` | Live research progress indicators |
| `SearchImages.tsx` | Image grid with lightbox |
| `SearchVideos.tsx` | Video results with thumbnails and duration |
| `WeatherWidget.tsx` | Open-Meteo API, geolocation, 5-day forecast |
| `StockWidget.tsx` | Ticker search, price display, day stats |
| `WidgetCard.tsx` | Calculator, unit conversion, definitions |
| `ToastProvider.tsx` | Toast notifications (success/error/warning/info) |

## Shared Utilities

| File | Purpose |
|------|---------|
| `lib/api-service.ts` | API client — all backend calls + SSE streaming |
| `lib/utils.ts` | Shared helpers |
| `App.tsx` | Root component — routing, layout, state |
| `demo.tsx` | Full app orchestrator |
| `index.tsx` | Entry point |

## Project Structure

```
frontend/
├── components/        # All UI components (see table above)
│   └── ui/           # Shared primitives (buttons, inputs, etc.)
├── lib/              # API service, utilities
├── App.tsx           # Root component
├── demo.tsx          # App orchestrator
├── index.tsx         # Entry point
├── index.html        # HTML template
├── vite.config.ts    # Vite configuration
├── tsconfig.json     # TypeScript configuration
├── tailwind.config.ts # Tailwind configuration
└── package.json      # Dependencies and scripts
```
