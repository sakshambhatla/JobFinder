# tests — Claude Context

Backend test suite using pytest. Covers resume parsing, ATS fetchers, storage, config, and all API routes.

## Running Tests
```bash
source .venv/bin/activate && pytest tests/ -v --tb=short
```
Install deps: `pip install -e ".[dev]"`

## File Map

| File | Coverage |
|------|----------|
| `test_resume_parser.py` | Regex extraction from .txt resumes — skills, titles, experience |
| `test_ats_fetchers.py` | Greenhouse, Lever, Ashby fetchers — httpx_mock for API responses |
| `test_api_resume.py` | `/api/resume` endpoints — upload, GET, DELETE |
| `test_api_companies.py` | `/api/companies` endpoints — discover, GET, registry |
| `test_api_roles.py` | `/api/roles` endpoints — discover, GET, checkpoint, browser-agent kill |
| `test_company_runs.py` | Company run history — CRUD + pagination |
| `test_api_cors.py` | CORS header validation — allowed origins |
| `test_config.py` | Config loading — file + CLI flag + env overrides; API key resolution |
| `test_local_filters.py` | Fuzzy (rapidfuzz) + semantic (fastembed) filtering; metro aliases |
| `test_storage.py` | JSON + Supabase backends — atomic writes, RLS simulation |
| `test_browser_agent_pipeline.py` | Browser agent streaming, kill signals, rate-limit backoff |
| `test_schema_sync.py` | Pydantic models vs Supabase table columns |
| `test_yc_source.py` | YC Jobs RapidAPI integration — mocked responses |

## Shared Fixtures (`conftest.py`)

| Fixture | What it provides |
|---------|-----------------|
| `tmp_data_dir` | Isolated temp directory per test |
| `test_config` | `AppConfig` pointing at `tmp_data_dir`, no real API keys |
| `store` | `JsonStorageBackend` backed by `tmp_data_dir` |
| `client` | FastAPI `TestClient` with patched `load_config` + `get_storage_backend` across all route modules |
| `greenhouse_fixture` / `lever_fixture` / `ashby_fixture` / `ycombinator_fixture` | JSON from `tests/fixtures/` |

## Key Patterns

- **API tests**: use `client` fixture — it patches `load_config` and `get_storage_backend` across all route modules so tests hit temp storage, not real data
- **ATS tests**: use `httpx_mock` (from `pytest-httpx`) to intercept `httpx` calls; verify `DiscoveredRole` output
- **Config tests**: `monkeypatch` environment variables
- **Schema sync**: verifies Pydantic field names match Supabase column names
- **No network calls**: all external HTTP is mocked; never use real API keys in tests

## Fixtures Directory

`tests/fixtures/` contains JSON snapshots of real ATS API responses:
- `greenhouse_jobs.json`, `lever_jobs.json`, `ashby_jobs.json`, `ycombinator_jobs.json`

## Adding a New Test

1. Create `tests/test_<feature>.py`
2. Use existing fixtures from `conftest.py` where possible
3. For API route tests: use the `client` fixture (auto-patches config + storage)
4. For external HTTP: use `httpx_mock` or `unittest.mock.patch`
5. Never use real API keys or make real network calls
