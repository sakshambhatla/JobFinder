# data/ — Runtime Data Files

All files in this directory are runtime-generated and ignored by git.
Modify `jobfinder/storage/schemas.py` before changing any data shapes.

## Files

| File | Source | Description |
|------|--------|-------------|
| `resumes.json` | `jobfinder resume` | Parsed resume data. |
| `companies.json` | `jobfinder discover-companies` | Discovered companies with ATS metadata. |
| `company_registry.json` | Discovery & Roles | Perpetual registry of companies across runs. |
| `roles.json` | `jobfinder discover-roles` | Fetched, filtered, and scored roles. |
| `roles_checkpoint.json` | `discover-roles` | Transient checkpoint for rate limiting recovery. |
| `api_profiles.json` | Browser Agent | Discovered career page API endpoints for prompt injection. |

## `company_registry.json` Logic
- **Lookup**: Matched by `name.lower()`.
- **Updates**: `discover-companies` updates all fields except `searchable`.
- **Searchable**: Updated only by `discover-roles` after an actual attempt.

## Merge Strategy
- **Deduplication**: Companies by name, roles by URL.
- **Precedence**: New results override old ones. ATS data takes precedence over browser-agent data.
- **Sorting**: Roles are always sorted by `relevance_score` descending in the final output.
