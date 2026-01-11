# AutoApply

Automated job application preparation system. Ingests job postings from RSS feeds, extracts keywords, generates tailored resumes, and prefills application forms for manual review.

**Use this when:**
- You're processing 10+ job applications weekly
- Job boards you target expose RSS feeds
- You maintain a LaTeX resume you want to customize per job
- You want form data captured but control final submission

---

## Features

- **RSS ingestion** – Polls configured feeds hourly, deduplicates by URL
- **LLM-driven scraping** – Extracts job descriptions using browser automation (Gemini Flash)
- **Keyword extraction** – Identifies skills/requirements, injects into LaTeX template
- **PDF compilation** – Renders tailored resume via `pdflatex`
- **Form prefilling** – Navigates application pages, fills fields from profile data
- **Draft persistence** – Saves form state to SQLite; resume later from any device
- **Chrome extension** – Rehydrates saved drafts on actual job board pages
- **No auto-submit** – Automation stops before submission; user reviews and submits

---

## Tech Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Backend | Python 3.11 / FastAPI | Async-first, simple dependency injection |
| Frontend | Next.js 16 / React 19 | Server components, fast iteration |
| Database | SQLite | Zero-config, ACID, sufficient for single-user workloads |
| Browser automation | browser-use + Playwright | LLM-driven DOM interaction; adapts to unknown job boards |
| LLM provider | OpenRouter (Gemini/Llama) | Model-agnostic routing, cost control |
| Resume engine | Jinja2 + pdflatex | Deterministic PDF output from LaTeX source |
| Container | Docker Compose | Single-command deployment |

---

## Architecture

| Component | Responsibility |
|-----------|----------------|
| `RSSWatcher` | Polls feeds, publishes new job events |
| `JobManager` | Tracks job state machine in SQLite (`Pending → Running → Draft Saved / Failed`) |
| `DraftManager` | Stores form field snapshots with timestamps and status |
| `BrowserAgent` | LLM-controlled browser for scraping and prefilling |
| `ResumeBuilder` | Extracts keywords via LLM, renders LaTeX, compiles PDF |
| `FastAPI server` | REST endpoints for jobs, drafts, profile, feeds, settings |
| `Next.js frontend` | Dashboard for job queue, draft review, profile editing |
| `Chrome extension` | Injects saved drafts into live job board forms |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                USER LAYER                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────┐   │
│  │   Browser    │    │   Next.js    │    │     Chrome Extension         │   │
│  │  (Manual)    │    │   Frontend   │    │  (Draft Rehydration)         │   │
│  └──────────────┘    └──────┬───────┘    └──────────────┬───────────────┘   │
└─────────────────────────────┼───────────────────────────┼───────────────────┘
                              │ HTTP                      │ HTTP
┌─────────────────────────────┼───────────────────────────┼───────────────────┐
│                             ▼                           ▼                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Server (:8000)                       │   │
│  │   /jobs  /drafts  /feeds  /profile  /settings  /upload-*            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│         ┌────────────────────┼────────────────────┐                         │
│         ▼                    ▼                    ▼                         │
│  ┌─────────────┐     ┌─────────────┐      ┌─────────────┐                   │
│  │ JobManager  │     │DraftManager │      │ ConfigMgr   │                   │
│  └──────┬──────┘     └──────┬──────┘      └──────┬──────┘                   │
│         │                   │                    │                          │
│         └───────────────────┼────────────────────┘                          │
│                             ▼                                               │
│                    ┌────────────────┐                                       │
│                    │  SQLite (jobs.db)                                      │
│                    │  jobs | drafts │                                       │
│                    └────────────────┘                                       │
│                                                                   BACKEND   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          BACKGROUND AUTOMATION LOOP                         │
│                                                                             │
│   ┌───────────┐      ┌──────────────┐      ┌──────────────┐                 │
│   │  RSS      │─────▶│  RSSWatcher  │─────▶│ JobManager   │                 │
│   │  Feeds    │      │  (hourly)    │      │ (add pending)│                 │
│   └───────────┘      └──────────────┘      └──────────────┘                 │
│                                                   │                         │
│                                                   ▼                         │
│                                          ┌──────────────┐                   │
│                                          │ Pending Jobs │                   │
│                                          └───────┬──────┘                   │
│                                                  │                          │
│   ┌──────────────────────────────────────────────┼──────────────────────┐   │
│   │              DraftPreparationService         ▼                      │   │
│   │  ┌─────────────┐   ┌───────────────┐   ┌─────────────┐              │   │
│   │  │ BrowserAgent│──▶│ ResumeBuilder │──▶│ BrowserAgent│              │   │
│   │  │  (scrape)   │   │   (LaTeX)     │   │  (prefill)  │              │   │
│   │  └─────────────┘   └───────────────┘   └──────┬──────┘              │   │
│   └───────────────────────────────────────────────┼─────────────────────┘   │
│                                                   ▼                         │
│                                          ┌──────────────┐                   │
│                                          │ Draft Saved  │                   │
│                                          └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘

Data Flow: RSS → JobManager → BrowserAgent → ResumeBuilder → BrowserAgent → DraftManager
```

---

## Workflow

1. **User configures RSS feeds** via frontend (`/feeds`)
2. **RSSWatcher polls** feeds hourly, inserts new job URLs as `Pending`
3. **Automation loop picks up** `Pending` job (every 60s)
4. **BrowserAgent scrapes** job page, extracts description via LLM
5. **ResumeBuilder extracts** keywords, injects into LaTeX, compiles PDF
6. **BrowserAgent navigates** to application form, prefills fields from `profile.json`
7. **DraftManager saves** FormState (field IDs, values, confidence scores)
8. **Job status transitions** to `Draft Saved`
9. **User opens draft** in frontend or Chrome extension
10. **Browser rehydrates** fields; user reviews, edits, submits manually

**On failure:**
- Steps 4–7: Job marked `Draft Failed`, error stored in `error_message` column
- LaTeX errors: Compilation halts, job fails, user corrects template
- LLM timeout: Job stays failed; reset to `Pending` via API to retry
- Partial scrape: Draft saved with `EXTRACTED` status; form fields empty

---

## Code Structure

```
.
├── backend/
│   ├── api/
│   │   ├── routers/          # FastAPI route handlers (jobs, drafts, feeds, profile, settings)
│   │   ├── schemas/          # Pydantic models for request/response validation
│   │   ├── server.py         # App entrypoint, lifespan, middleware
│   │   └── dependencies.py   # DI factories
│   ├── src/
│   │   ├── agent.py          # BrowserAgent – LLM-driven browser automation
│   │   ├── rss_watcher.py    # RSS polling and event publishing
│   │   ├── job_manager.py    # SQLite persistence for job state
│   │   ├── draft_manager.py  # SQLite persistence for form drafts
│   │   ├── resume_builder.py # Keyword extraction + LaTeX compilation
│   │   ├── services.py       # DraftPreparationService orchestration
│   │   ├── database.py       # SQLite connection and schema init
│   │   └── config.py         # ConfigManager for feeds/settings
│   ├── data/                 # Runtime data (jobs.db, profile.json, generated PDFs) ⚠️
│   ├── tests/                # pytest suite (safe to modify)
│   └── requirements.txt
├── frontend/
│   ├── app/                  # Next.js App Router pages
│   ├── components/           # Reusable UI (shadcn/ui-based)
│   └── lib/                  # Utilities
├── chrome-extension/
│   ├── background.js         # Fetches draft data from API
│   ├── content.js            # Injects saved values into job board forms
│   └── manifest.json
├── data/                     # Mounted volume for persistent state ⚠️
└── docker-compose.yml
```

**Safe to modify:** `tests/`, `frontend/components/`, `frontend/app/`, routers  
**Risky:** `database.py` (schema changes), `agent.py` (LLM prompts), `resume_builder.py` (LaTeX logic)  
**Do not delete:** `data/jobs.db`, `data/profile.json`

---

## Setup

### Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.11+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| pdflatex | Any | `pdflatex --version` |
| Chromium | Latest | Installed via Playwright |

### Environment

```bash
# Required
echo "OPENROUTER_API_KEY=sk-or-..." > .env
```

### Local Setup

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

# Start backend (terminal 1)
uvicorn api.server:app --host 0.0.0.0 --port 8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

### Docker Setup

```bash
docker compose up --build
```

### Verify

| Check | Expected |
|-------|----------|
| `curl http://localhost:8000/jobs` | `[]` or list of jobs |
| `http://localhost:3000` | Dashboard loads |
| Add RSS feed in `/feeds` | Feed appears in list |
| Wait 1 minute | Jobs appear in `/jobs` with `Pending` status |

---

## Constraints

- **Single-user only** – No authentication; deploy behind VPN or auth proxy
- **Single browser instance** – Concurrent automation not supported
- **No auto-retry** – Failed jobs stay failed; reset manually via `PATCH /jobs/{url}`
- **LLM-dependent** – Form filling quality varies by job board DOM structure
- **Captcha-blocked** – Sites with hCaptcha/Cloudflare may require headed mode and manual intervention
- **No scheduling** – Use external cron/systemd to start/stop the server if needed
