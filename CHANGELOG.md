# Changelog

All notable changes to JobFinder are documented here.

---

## [v3.0.0] — 2026-03-20

External job source integration and startup-focused discovery.

### Major Features

- **Y Combinator Jobs API**: Fetches recent YC startup jobs via RapidAPI as a new "Pass 0" in the role discovery pipeline, before per-company ATS fetching
- **External job sources abstraction**: Extensible `jobfinder/roles/sources/` package with registry pattern for adding future RapidAPI integrations
- **Startups focus toggle**: New "Regular / Startups" selector in Company Discovery UI; tagging a run as "Startups" auto-enables YC Jobs during role discovery
- **External job cache**: Per-source cache with configurable TTL (12h for YC); stored in `external_job_cache.json` / Supabase table

### Other Changes

- Added `--enable-yc-jobs` CLI flag for `discover-roles`
- Added `RAPIDAPI_KEY` server-level env var for YC Jobs API access
- Updated startup resume (all-startup experience: Retool, Brex, PlanGrid)
- Split UAT skill into `uat-companies` and `uat-roles` for targeted testing
- Pagination safety cap (MAX_ROLES=1000) on external source fetchers
- Supabase migration for `external_job_cache` table with RLS

---

## [v2.0.0] — 2026-03-18

JobFinder is no longer single-player. This release introduces a full managed mode powered by Supabase, transforming JobFinder from a local CLI tool into a multi-user web application with authentication, persistent cloud storage, and a significantly overhauled UI.

### Major Features

- **Managed mode with Supabase**: Postgres-backed storage with Row-Level Security (RLS) — each user's data is fully isolated
- **Authentication**: Supabase Auth integration with login page, JWT-based API auth (JWKS, supports ES256/RS256/HS256), and per-user session handling
- **Profile pictures**: Upload and store avatars via Supabase Storage
- **Company & job run history**: Track every discovery run with Tier 1/Tier 2 role counts, surfaced in the run history UI
- **Local filters**: Client-side semantic filtering for roles (title, location, date) without burning LLM calls
- **Per-user log streaming**: SSE log streams isolated per user session
- **Vault-based API key storage**: Users store their own LLM API keys securely via Supabase Vault (SECURITY DEFINER functions) with graceful fallback if vault is not yet installed

### UI Overhaul

- Mode selection page (local vs managed)
- Login page, profile menu, and "My Profile" modal
- API keys management dialog
- Job search preferences modal
- Dropdown menu component (shadcn/ui)
- Run history with Tier 1/Tier 2 role breakdowns in Companies and Roles tabs
- Automatic JWT refresh with retry on 401 responses

### Security Hardening

- JWT verification via JWKS — no longer requires `SUPABASE_JWT_SECRET` env var
- CORS tightened to explicit method/header allowlist
- `api_profiles` domain validation to reject foreign-domain endpoint injection
- Per-user API key isolation in managed mode (no server env var fallback)
- Resume filename sanitization to prevent path traversal attacks

### Infrastructure

- 7 Supabase migrations: schema, RLS, vault functions, company/job runs, profile pictures, roles unique constraint, api_profiles audit trail
- `scripts/apply_vault_migration.py` helper for applying vault SQL via psql
- 4 new Claude Code skills: `add-ats-fetcher`, `add-api-endpoint`, `supabase-migration`, `run-all-checks`
- UAT skill + fixture for end-to-end managed-mode acceptance testing
- CORS, schema-sync, and api_profiles domain validation test suites added

### Bug Fixes

- Roles upsert no longer overwrites unfiltered rows
- Searchable flags now correctly set after ATS success
- Supabase backend uses anon key + per-user JWT instead of service role key
- Vault migration no longer attempts `CREATE EXTENSION` (pre-installed on Supabase)

---

## [v1.0.0] — initial release

Local-mode CLI tool for discovering relevant companies and open roles from a resume. Single-user, JSON file storage, Anthropic and Gemini provider support, ATS fetchers, semantic/LLM/fuzzy role filtering, browser agent fallback for JS-heavy career pages.
