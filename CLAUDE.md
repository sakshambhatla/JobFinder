# JobFinder — Claude Context

## Stack
- **Backend**: Python 3.12 · FastAPI · uvicorn · Click · Pydantic v2 · httpx · Rich · Anthropic SDK · google-genai
- **Frontend**: React 18 · TypeScript · Vite · Tailwind CSS v4 · shadcn/ui · TanStack Query · TanStack Table · axios
- Install: `source .venv/bin/activate && pip install -e .`
- Entry points: `jobfinder/cli.py` (CLI) · `jobfinder/api/main.py` (FastAPI)

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
  api/          # → see jobfinder/api/CLAUDE.md
  resume/       # parse_resumes(dir) — regex extraction from .txt files
  companies/    # discover_companies(resumes, config) — LLM → JSON → DiscoveredCompany[]
  roles/        # → see jobfinder/roles/CLAUDE.md
  storage/
    schemas.py  # ALL Pydantic models — edit here first when changing data shapes
    store.py    # StorageManager: atomic JSON read/write
  utils/
    http.py     # get_json(url, timeout) with retry
    display.py  # Rich console helpers
    throttle.py # Shared RateLimiter; get_limiter(rpm) — process-level singleton
ui/             # → see ui/CLAUDE.md
```

## Config (`config.json`)
All fields optional. CLI flags override file values.
```
model_provider        "anthropic" | "gemini"
anthropic_model       string
gemini_model          string
max_companies         int
refresh               bool
request_timeout       int                   seconds
resume_dir            path
data_dir              path
role_filters.title    string | null         semantic job title filter
role_filters.posted_after  string | null   natural language date
role_filters.location string | null        natural language location(s)
role_filters.confidence  "high"|"medium"|"low"   default "high"
relevance_score_criteria  string | null    LLM scores roles 1–10, sorted highest-first
write_preference      "overwrite"|"merge"  merge deduplicates + re-sorts; default "overwrite"
rpm_limit             int                  client-side throttle; 0 = off; default 4
```
API keys from env only: `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`.

## Cross-Cutting Patterns
- **Schemas first**: change `storage/schemas.py` before touching discovery/API/UI code
- **Multi-provider**: add `_call_<provider>()` + branch in each `discovery.py`, plus key check in `config.py:require_api_key()`
- **Graceful degradation**: ATS failures → `flagged` list, not crashes
- **API mirrors CLI**: routes call the same core functions; blocking calls wrapped in `asyncio.to_thread()`
