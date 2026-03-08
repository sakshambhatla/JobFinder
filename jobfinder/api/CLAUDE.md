# jobfinder/api — Claude Context

FastAPI layer that wraps the existing Python core functions and serves the React UI.

## File Map
```
main.py       # App factory: CORS, router mounting, StaticFiles for ui/dist
models.py     # Request-only Pydantic models (responses use storage/schemas.py directly)
routes/
  resume.py   # POST /api/resume/upload · GET /api/resume
  companies.py# POST /api/companies/discover · GET /api/companies
  roles.py    # POST /api/roles/discover · GET /api/roles
```

## Endpoints

| Method | Path | What it does |
|--------|------|--------------|
| POST | `/api/resume/upload` | Clears `resume_dir/*.txt`, saves new file, calls `parse_resumes()`, writes `resumes.json` |
| GET | `/api/resume` | Reads `resumes.json`, 404 if absent |
| POST | `/api/companies/discover` | Merges request overrides into config, calls `discover_companies()`, applies merge logic, writes `companies.json` |
| GET | `/api/companies` | Reads `companies.json`, 404 if absent |
| POST | `/api/roles/discover` | Fetches ATS roles, applies filters + scoring, applies merge logic, writes `roles.json` |
| GET | `/api/roles` | Reads `roles.json`, 404 if absent |

## Key Patterns

**Blocking calls → thread pool**: all LLM and HTTP-heavy functions are sync; wrap with `asyncio.to_thread()` to avoid blocking the FastAPI event loop:
```python
companies = await asyncio.to_thread(discover_companies, resumes, config)
```

**Config overrides**: build an `overrides` dict from request fields, pass as kwargs to `load_config(**overrides)`. Only include keys where the request value is not `None`.

**API key errors**: `require_api_key()` raises `SystemExit` (designed for CLI). Catch it and re-raise as `HTTPException(400)`:
```python
try:
    require_api_key(config.model_provider)
except SystemExit as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
```

**Merge logic**: duplicated from `cli.py` — dedup companies by `name.lower()`, roles by `url`. New results take precedence. Sort roles by `relevance_score` descending.

**Production static files**: `main.py` mounts `ui/dist/` at `/` only if the directory exists — so the server works fine during development without a built UI.

## Adding a New Endpoint
1. Add request model to `models.py` (if needed)
2. Create handler in `routes/<name>.py`; import and include its router in `main.py`
3. Mirror the same logic in `cli.py` if it should also be a CLI command
4. Add the API call + TypeScript type to `ui/src/lib/api.ts`
