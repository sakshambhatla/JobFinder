# jobfinder/roles — Gemini Context

Handles role fetching from ATS APIs, LLM-based filtering, and relevance scoring.

## File Map
```
discovery.py   # discover_roles(companies, config) → (DiscoveredRole[], FlaggedCompany[])
filters.py     # filter_roles(roles, filters, config) → DiscoveredRole[]
scorer.py      # score_roles(roles, criteria, config) → DiscoveredRole[] (sorted)
ats/
  __init__.py       # ATS_REGISTRY: ats_type → fetcher instance
  base.py           # BaseFetcher ABC; error types
  greenhouse.py     # greenhouse API fetcher
  lever.py          # lever API fetcher
  ashby.py          # ashby API fetcher
  unsupported.py    # raises UnsupportedATSError
  browser_session.py# AgentSession, metrics, rate limits
  career_page.py    # HTML scraping + Tier 3 browser agent
```

## ATS Fetching (`discovery.py`)
- Uses `ATS_REGISTRY` for lookup based on `company.ats_type`.
- Unsupported or failing ATS → company added to `flagged` list.
- Supported ATS (Greenhouse, Lever, Ashby) use public APIs.

**Adding a new ATS:**
1. Implement `ats/<name>.py` subclassing `BaseFetcher`.
2. Register in `ATS_REGISTRY` in `ats/__init__.py`.
3. Update `DiscoveredCompany.ats_type` in `storage/schemas.py`.
4. Update LLM prompt in `companies/prompts.py`.

## LLM Filtering (`filters.py`)
- **Batching**: 100 roles per call.
- **Input**: `title | location | date`.
- **Output**: JSON indices of matching roles.
- **Confidence**: `high`, `medium`, `low` (affects prompt strictness).
- **Throttling**: Respects `config.rpm_limit`.

## LLM Scoring (`scorer.py`)
- **Batching**: 60 roles per call.
- **Input**: `title | company | location | dept`.
- **Output**: JSON object with scores (1–10) and summaries (≤15 words).
- **Sorting**: Returns roles sorted by `relevance_score` descending.

## Browser Agent (Tier 3)
- Used when APIs or scraping are unavailable.
- **Streaming**: `_StreamingLLMWrapper` intercepts LLM calls to emit `jobs_batch` events in real-time.
- **Killing**: Agent task polls `session.kill_event` for clean cancellation.
- **Budget**: Time budget enforced by `asyncio.wait_for`.
- **API Profiles**: Successful discoveries are cached in `data/api_profiles.json` and injected into subsequent prompts to skip discovery.
