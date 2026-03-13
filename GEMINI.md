# JobFinder — Gemini Context

## Stack
- **Backend**: Python 3.12 · FastAPI · uvicorn · Click · Pydantic v2 · httpx · Rich · Anthropic SDK · google-genai
- **Frontend**: React 18 · TypeScript · Vite · Tailwind CSS v4 · shadcn/ui · TanStack Query · TanStack Table · axios
- **Install**: `source .venv/bin/activate && pip install -e .`
- **Entry points**: `jobfinder/cli.py` (CLI) · `jobfinder/api/main.py` (FastAPI)

## Commands
| Command | Output | Key flags |
|---------|--------|-----------|
| `jobfinder resume` | `data/resumes.json` | `--resume-dir` |
| `jobfinder discover-companies` | `data/companies.json` | `--max-companies`, `--refresh` |
| `jobfinder discover-roles` | `data/roles.json` | `--company`, `--refresh` |
| `jobfinder serve` | HTTP server | `--host`, `--port`, `--reload` |

## Top-Level Map
```
jobfinder/
  cli.py        # 4 Click subcommands; thin wrappers around core functions
  config.py     # AppConfig (Pydantic) — see Config section below
  api/          # → see jobfinder/api/GEMINI.md
  resume/       # parse_resumes(dir) — regex extraction from .txt files
  companies/    # discover_companies(resumes, config) — LLM → JSON → DiscoveredCompany[]
  roles/        # → see jobfinder/roles/GEMINI.md
  storage/
    schemas.py      # ALL Pydantic models — edit here first when changing data shapes
    store.py        # StorageManager: atomic JSON read/write
    api_profiles.py # load/save discovered career-page API endpoints (data/api_profiles.json)
  utils/
    http.py     # get_json(url, timeout) with retry
    display.py  # Rich console helpers
    throttle.py # Shared RateLimiter; get_limiter(rpm) — process-level singleton
ui/             # → see ui/GEMINI.md
```

## Config (`config.json`)
All fields optional. CLI flags override file values.
```json
{
  "model_provider": "anthropic" | "gemini",
  "anthropic_model": "string",
  "gemini_model": "string",
  "max_companies": "int",
  "refresh": "bool",
  "request_timeout": "int",
  "resume_dir": "path",
  "data_dir": "path",
  "role_filters": {
    "title": "string | null",
    "posted_after": "string | null",
    "location": "string | null",
    "confidence": "high"|"medium"|"low"
  },
  "relevance_score_criteria": "string | null",
  "write_preference": "overwrite"|"merge",
  "rpm_limit": "int",
  "browser_agent_max_time_minutes": "int",
  "browser_agent_max_steps": "int",
  "browser_agent_rate_limit_max_retries": "int",
  "browser_agent_rate_limit_initial_wait": "int"
}
```
API keys from env only: `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`.

## Cross-Cutting Patterns
- **Schemas first**: Always update `jobfinder/storage/schemas.py` before modifying discovery, API, or UI code.
- **Multi-provider**: When adding provider-specific logic, use `_call_<provider>()` and branch in `discovery.py`. Ensure API keys are checked in `config.py:require_api_key()`.
- **Graceful degradation**: ATS failures should result in entries in the `flagged` list rather than crashing the application.
- **API mirrors CLI**: Ensure API routes call the same core functions as the CLI. Wrap blocking calls in `asyncio.to_thread()`.

## Testing Convention
After any major code change, run both backend and frontend tests:

### Backend (CLI & API)
```bash
# Activate venv and run pytest
source .venv/bin/activate && pytest tests/ -v --tb=short
```
- Covers: resume parser, ATS fetchers, storage, config, API routes.

### Frontend (UI)
```bash
# Run vitest in the ui directory
pnpm --dir ui test
```
- Covers: ResumeTab rendering and API helpers.

Both suites must pass before committing changes.
