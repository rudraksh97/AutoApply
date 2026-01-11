# AutoApply

An automated job application system that discovers job postings via RSS, generates tailored resumes using LLM-extracted keywords, and submits applications through browser automation.

## Overview

AutoApply solves a specific problem: applying to many similar jobs requires repetitive work that can be automated without sacrificing quality. The system watches RSS feeds for new postings, extracts requirements from job descriptions, generates ATS-optimized resumes by injecting relevant keywords into a LaTeX template, and uses a headless browser agent to complete application forms.

This is not a "spray and pray" tool. It is designed for targeted automation where you control the sources (RSS feeds), the resume template, and your profile data. The LLM tailors each resume to the specific job description.

## Non-Goals

- **Universal job board support.** The browser agent works best with structured application forms. Complex multi-step applications with CAPTCHAs or unusual flows will fail.
- **Resume generation from scratch.** You provide a LaTeX template; the system injects keywords. It does not write your experience or achievements.
- **Scheduling or cron.** The system runs when started. External scheduling (systemd, cron, Kubernetes CronJob) is your responsibility.
- **User authentication.** The API has no auth. Run it behind a reverse proxy with authentication in production.
- **Persistent queuing.** Job state is stored in a JSON file. At scale, this will not work.

## Core Concepts

### Job Lifecycle

```
Pending → Running - Scraping → Running - Generating Resume → Running - Applying → Completed | Failed
```

Each job URL transitions through these states. The `JobManager` persists state to `data/jobs.json`. A job can be retried by resetting its status to `Pending`.

### Components

| Component | Responsibility |
|-----------|----------------|
| `RSSWatcher` | Polls configured RSS feeds, yields new URLs not already in job store |
| `BrowserAgent` | Wraps browser-use library; scrapes job pages and fills application forms |
| `ResumeBuilder` | Extracts keywords via LLM, renders LaTeX template, compiles to PDF |
| `JobManager` | CRUD operations on `data/jobs.json` |
| `ProfileManager` | Stores user profile data for form-filling |
| `ConfigManager` | Manages RSS feed URLs and API keys |

### Invariants

- A job URL appears in `jobs.json` at most once.
- Once a job enters `Running-*` state, no other process should pick it up.
- The LLM call in `ResumeBuilder` must return valid JSON with a `skills_list` key.
- The LaTeX template must contain `\VAR{skills_list}` as a placeholder.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Frontend (Next.js)                        │
│                          localhost:3000                             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                            │
│                         localhost:8000                              │
│  ┌──────────────┬──────────────┬──────────────┬──────────────────┐  │
│  │  /api/jobs   │  /api/feeds  │ /api/profile │  /ws/logs        │  │
│  └──────────────┴──────────────┴──────────────┴──────────────────┘  │
│                                    │                                │
│  ┌─────────────────────────────────┴──────────────────────────────┐ │
│  │                     Automation Loop                             │ │
│  │  RSSWatcher → BrowserAgent.scrape → ResumeBuilder → apply      │ │
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
        data/jobs.json       data/profile.json      data/config.json
```

### Data Flow

1. `RSSWatcher` fetches feeds, compares entries against `jobs.json`, yields new URLs.
2. New URLs are persisted as `Pending`.
3. Main loop picks up `Pending` jobs and calls `process_job()`.
4. `BrowserAgent.scrape_job_details()` opens the URL, extracts job description via LLM.
5. `ResumeBuilder.build()` calls LLM to extract keywords, renders template, compiles PDF.
6. `BrowserAgent.apply_to_job()` fills the application form using profile data.
7. Job status updated to `Completed` or `Failed`.

### API Boundaries

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/jobs` | GET | List all jobs with status |
| `/api/jobs/{url}/retry` | POST | Reset job to Pending |
| `/api/feeds` | GET/POST/DELETE | Manage RSS feed URLs |
| `/api/profile` | GET/PUT | Read/write user profile |
| `/start` | POST | Begin automation (optionally continuous) |
| `/stop` | POST | Signal automation to stop |
| `/ws/logs` | WebSocket | Real-time log streaming |
| `/upload-template` | POST | Upload LaTeX resume template |

## Design Decisions

### LLM via OpenRouter

The system uses OpenRouter as an LLM gateway, defaulting to `meta-llama/llama-3.3-70b-instruct:free`. This was chosen for cost and flexibility.

**Trade-off:** Free-tier models have rate limits and lower reliability. For production use, switch to a paid model or self-hosted LLM.

### JSON File Persistence

Job state lives in `data/jobs.json`. This is simple and requires no external dependencies.

**Trade-off:** No concurrency safety. Multiple processes modifying the file will corrupt state. At scale (>1000 jobs), reads become slow. Migrate to SQLite or Postgres if needed.

### browser-use Library

Browser automation uses the `browser-use` library, which provides an agent abstraction over Playwright.

**Trade-off:** The agent is LLM-driven, meaning it interprets page structure at runtime. This is flexible but unpredictable. Some application forms will fail. The agent can also be slow due to multiple LLM round-trips.

### Headless by Default

Production runs headless. There is no flag to change this at runtime; modify `BrowserAgent.__init__()` if you need headed mode for debugging.

### No Queue / No Workers

The system processes jobs serially in a single async loop. This is intentional for simplicity.

**Trade-off:** Throughput is limited. If you need parallelism, refactor to use a proper job queue (Celery, RQ, or similar).

## Operational Model

### Startup

1. Backend loads `.env` (requires `OPENROUTER_API_KEY`).
2. FastAPI mounts static files from `data/`.
3. On `/start`, spawns background task running `run_auto_apply()`.
4. WebSocket clients can connect to `/ws/logs` for real-time output.

### Failure Modes

| Failure | Behavior | Recovery |
|---------|----------|----------|
| LLM API error | Job marked `Failed` with error message | Retry via API |
| Browser timeout | Job marked `Failed` | Retry; consider increasing timeouts |
| Invalid LaTeX | PDF compilation fails, job marked `Failed` | Fix template, retry |
| RSS parse error | Logged and skipped | Fix feed URL |
| JSON corruption | Manager returns empty list | Restore from backup or delete file |

### Graceful Shutdown

Calling `/stop` sets an `asyncio.Event`. The main loop checks this event during sleep intervals and exits cleanly.

### Logging

Logs are emitted via callback and broadcast over WebSocket. There is no file-based logging by default. For production, wrap with a proper logging handler.

## Extensibility

### Adding New Job Sources

Implement a source that yields job URLs and call `job_manager.add_job(url)`. The existing loop will pick them up.

### Custom Resume Templates

1. Create a `.tex` file with Jinja2 placeholders using `\VAR{...}` syntax.
2. Required placeholder: `\VAR{skills_list}` (list of strings).
3. Upload via `/upload-template` or place at `data/resume_base.tex`.

### Swapping LLMs

Modify `OpenRouterLLM` in `src/agent.py` or `ResumeBuilder` in `src/resume_builder.py`. The system expects `langchain`-compatible chat models.

### Alternative Persistence

Replace `JobManager._load()` and `_save()` with database calls. The interface is simple: `get_all_jobs()`, `add_job()`, `update_job()`, `job_exists()`.

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- pdflatex (for resume compilation)
- Chromium (installed via playwright)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

Create `.env` in project root:

```
OPENROUTER_API_KEY=your_key_here
```

Run:

```bash
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker-compose up --build
```

Backend available at `localhost:8000`, frontend at `localhost:3000`.

## Testing & Validation

### What Is Tested

- Integration test in `tests/test_job_workflow.py` exercises the real browser agent and LLM against a live job URL.
- Run with: `cd backend && source venv/bin/activate && pytest tests/ -v -s`

### What Is Not Tested

- Unit tests for individual managers (JSON I/O is trivial).
- Frontend tests (no test suite exists).
- LLM output correctness (non-deterministic).

### Manual Validation

1. Add an RSS feed via the UI.
2. Start automation.
3. Verify job appears in list, progresses through states.
4. Download generated PDF and inspect for keyword injection.

## Known Limitations

1. **No authentication.** The API is open. Do not expose to the public internet without a reverse proxy.
2. **Single-process.** Cannot scale horizontally without external coordination.
3. **LLM-dependent browser agent.** Some application forms are too complex and will fail silently.
4. **Free-tier LLM limits.** Expect failures under load or after extended use.
5. **No retry backoff.** Failed jobs stay failed until manually retried.
6. **LaTeX dependency.** Host must have `pdflatex` installed and in PATH.
7. **No input validation.** Malformed profile data or feed URLs can cause runtime errors.

## Future Work

Scoped items that would improve the system without fundamental redesign:

1. **SQLite persistence.** Replace JSON files with SQLite for atomicity and query support.
2. **Exponential backoff on LLM failures.** Prevent cascading failures under rate limits.
3. **Job deduplication by content hash.** Same job posted to multiple feeds gets processed once.
4. **Template validation endpoint.** Check for required placeholders before accepting upload.
5. **Structured logging.** JSON logs with correlation IDs for debugging.
6. **Health endpoint.** `/health` returning system status for load balancer probes.
7. **Rate limiting.** Per-source throttling to avoid being blocked by job boards.

---

*This system was designed to be understood, operated, and modified by engineers who read the code. When in doubt, read the source.*
