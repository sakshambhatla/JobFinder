# jobfinder/api — Gemini Context

FastAPI layer wrapping core Python functions to serve the React UI.

## File Map
```
main.py       # App factory: CORS, router mounting, StaticFiles for ui/dist
models.py     # Request-only Pydantic models (responses use storage/schemas.py directly)
routes/
  resume.py   # POST /api/resume/upload · GET /api/resume
  companies.py# POST /api/companies/discover · GET /api/companies
  roles.py    # POST /api/roles/discover · GET /api/roles · GET /api/roles/fetch-browser/stream (SSE) · DELETE /api/roles/fetch-browser/{name} · POST /api/roles/fetch-browser
```

## Endpoints

| Method | Path | Action |
|--------|------|--------|
| POST | `/api/resume/upload` | Clears `resume_dir`, saves new file, parses, writes `resumes.json` |
| GET | `/api/resume` | Reads `resumes.json` |
| POST | `/api/companies/discover` | Merges request overrides into config, discovers companies, writes `companies.json` |
| GET | `/api/companies` | Reads `companies.json` |
| POST | `/api/roles/discover` | Fetches roles, applies filters/scoring, writes `roles.json` |
| GET | `/api/roles` | Reads `roles.json` |
| GET | `/api/roles/fetch-browser/stream` | SSE stream for browser agent; emits `jobs_batch`, `filter_result`, `score_result`, `done`, `killed`, `error` |
| DELETE | `/api/roles/fetch-browser/{company_name}` | Kills a running browser agent session |
| POST | `/api/roles/fetch-browser` | Non-streaming browser fetch (CLI-style) |

## Key Patterns

**Non-blocking API**: Wrap sync LLM/HTTP functions in `asyncio.to_thread()` to prevent blocking the event loop.
```python
companies = await asyncio.to_thread(discover_companies, resumes, config)
```

**SSE Streaming**: `GET /roles/fetch-browser/stream` uses `EventSourceResponse`. An async generator drains `session.event_queue`, performs filtering/scoring, and yields events. Ensure `score_result` is emitted before terminal events.

**Agent Lifecycle**: Live `AgentSession` objects are stored in `app.state.running_agents` (keyed by company name) and removed when the SSE generator completes.

**Config Overrides**: Construct an `overrides` dict from non-None request fields and pass to `load_config(**overrides)`.

**Error Handling**: Convert `SystemExit` from `require_api_key()` into `HTTPException(400)`.

## Adding a New Endpoint
1. Define request models in `models.py`.
2. Add route handlers in `routes/<name>.py` and include in `main.py`.
3. Keep `cli.py` in sync with any new backend functionality.
4. Update `ui/src/lib/api.ts` with the new API call and types.
