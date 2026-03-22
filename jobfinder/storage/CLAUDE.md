# jobfinder/storage — Claude Context

Data persistence layer with swappable backends (JSON files for local mode, Supabase Postgres for managed mode).

## File Map
```
schemas.py          # ALL Pydantic models — single source of truth for data shapes
                    # RULE: edit this file FIRST when changing any data model
backend.py          # StorageBackend protocol (read/write/exists/delete + user_id property)
store.py            # JsonStorageBackend: atomic JSON read/write via temp file + rename
                    # (aliased as StorageManager for backwards compat)
supabase_backend.py # SupabaseStorageBackend: maps collection filenames → Postgres tables + RLS
registry.py         # Company registry: load_or_bootstrap_registry(), upsert_registry(),
                    #   update_registry_searchable()
api_profiles.py     # load/save discovered career-page API endpoints; domain validation
vault.py            # Supabase Vault: store/get/delete per-user LLM API keys (SECURITY DEFINER)
__init__.py         # get_storage_backend(user_id, jwt_token) → JSON or Supabase backend
```

## StorageBackend Protocol

Defined in `backend.py`. Two implementations:

| Backend | When used | Backing store |
|---------|-----------|---------------|
| `JsonStorageBackend` | No `SUPABASE_URL` set (local mode) | JSON files in `data/` dir |
| `SupabaseStorageBackend` | `SUPABASE_URL` set + user auth (managed mode) | Postgres tables with RLS |

`get_storage_backend(user_id, jwt_token)` in `__init__.py` selects automatically. Uses `SUPABASE_PUBLISHABLE_KEY` + user JWT — never the service role key.

## Collection → Table Mapping (Supabase)

| Collection filename | Postgres table | Storage type |
|---------------------|----------------|-------------|
| `resumes.json` | `resumes` | Structured |
| `companies.json` | `companies` | Structured |
| `roles.json` | `roles` | Structured |
| `roles_unfiltered.json` | `roles` (is_filtered=false) | Structured |
| `company_registry.json` | `company_registry` | Structured |
| `api_profiles.json` | `api_profiles` | Structured |
| `roles_cache.json` | `roles_cache` | JSONB blob |
| `roles_checkpoint.json` | `checkpoints` | JSONB blob |
| `external_job_cache.json` | `external_job_cache` | Structured |

## Key Schemas (`schemas.py`)

Core models (all changes start here):
- `ParsedResume` — skills, job_titles, companies_worked_at, education, years_of_experience
- `DiscoveredCompany` — name, career_page_url, ats_type, ats_board_token, reason
- `DiscoveredRole` — company, title, location, url, ATS metadata, relevance_score, summary
- `CompanyRegistryEntry` — perpetual per-user company metadata with `searchable` flag
- `RolesCacheEntry` — cached roles with 2-day TTL per company+ATS
- `CompanyRun` / `JobRunMetrics` — discovery run history and metrics
- `KNOWN_ATS_TYPES` — set of recognized ATS type strings

## Company Registry (`registry.py`)

- `upsert_registry()` — merges new companies; new discovery wins all fields **except** `searchable`
- `searchable`: `null` = never attempted, `true` = found ≥1 job, `false` = page inaccessible or 0 jobs
- Registry only grows — entries are never removed by upsert

## Vault (`vault.py`) — Security Sensitive

- **Only code that uses `SUPABASE_SECRET_KEY`** (service role) — all other storage uses publishable key + JWT
- Calls SECURITY DEFINER SQL functions: `store_user_api_key`, `get_user_api_key`, `delete_user_api_key`, `has_user_api_keys`
- Graceful degradation: `_is_vault_missing()` detects if vault functions aren't installed; returns safe defaults (empty results, no errors)

## Adding a New Collection

1. Add Pydantic model to `schemas.py`
2. Add read/write handlers to `supabase_backend.py` (structured table or JSONB blob)
3. Create SQL migration in `supabase/migrations/` (→ see `supabase/migrations/CLAUDE.md`)
4. Include RLS policy in the migration if user-scoped
5. Update `data/CLAUDE.md` with the new file
