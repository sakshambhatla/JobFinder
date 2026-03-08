# jobfinder/roles — Claude Context

Handles everything after companies are discovered: fetching roles from ATS APIs, LLM filtering, and LLM relevance scoring.

## File Map
```
discovery.py   # discover_roles(companies, config) → (list[DiscoveredRole], list[FlaggedCompany])
filters.py     # filter_roles(roles, filters, config) → list[DiscoveredRole]
scorer.py      # score_roles(roles, criteria, config) → list[DiscoveredRole]  (sorted by score)
ats/
  __init__.py  # ATS_REGISTRY: dict[str, BaseFetcher] — maps ats_type → fetcher instance
  base.py      # BaseFetcher ABC; ATSFetchError, UnsupportedATSError
  greenhouse.py# boards-api.greenhouse.io/v1/boards/{token}/jobs
  lever.py     # api.lever.co/v0/postings/{company}?mode=json
  ashby.py     # api.ashbyhq.com/posting-api/job-board/{token}
  unsupported.py# raises UnsupportedATSError (Workday/LinkedIn/unknown)
```

## ATS Fetching (`discovery.py`)
- Iterates companies, looks up fetcher via `ATS_REGISTRY[company.ats_type]`
- `UnsupportedATSError` → added to `flagged` list with career page URL for manual check
- `ATSFetchError` or any exception → also added to `flagged`, processing continues
- All three supported ATS (Greenhouse, Lever, Ashby) are **explicitly public APIs** — no auth, no ToS risk

**Adding a new ATS:**
1. Create `ats/<name>.py` subclassing `BaseFetcher`, implement `fetch(company) -> list[DiscoveredRole]`
2. Add entry to `ATS_REGISTRY` in `ats/__init__.py`
3. Update `DiscoveredCompany.ats_type` literal in `storage/schemas.py`
4. Update the LLM prompt in `companies/prompts.py` so it can emit the new type

## LLM Filtering (`filters.py`)
- **Batch size**: 100 roles/call
- **Input per role**: `title | location | date` (minimal tokens)
- **Output**: JSON array of matching 0-based indices — e.g. `[0, 3, 7]`
- **Confidence levels**: `high` (strict) · `medium` · `low` (inclusive) — maps to different system prompt instructions
- **Throttled**: calls `get_limiter(config.rpm_limit).wait()` before every LLM call
- Filter criteria are all optional; if none are set, returns the full list unchanged

## LLM Scoring (`scorer.py`)
- **Batch size**: 60 roles/call
- **Input per role**: `title | company | location | dept` (no date — not relevant to relevance)
- **Output**: JSON object `{"0": {"score": 9, "summary": "Platform eng, Spark"}, ...}`
- Both `score` (1–10) and `summary` (≤15 words) come from a single call
- Sets `role.relevance_score` and `role.summary` on each `DiscoveredRole`
- Returns list sorted by `relevance_score` descending
- `max_tokens=1024` (raised from 512 to fit summaries for large batches)
- **Throttled**: same rate limiter as filters

## Shared Rate Limiter
All LLM `_call_anthropic()` / `_call_gemini()` functions in this package call:
```python
from jobfinder.utils.throttle import get_limiter
get_limiter(config.rpm_limit).wait()
```
The limiter is a process-level singleton, so filter + scorer calls share the same sliding window.
