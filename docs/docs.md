# JobFinder — Learnings & Pitfalls

Human-written notes on things Claude (and future contributors) should know.
Add entries here when you discover non-obvious behavior, gotchas, or operational lessons.

## Template

### [Date] Topic
**Context**: What you were doing
**Issue**: What went wrong or was surprising
**Fix/Lesson**: What to do instead

---

### 2026-03-22 Supabase column additions require 3-file lockstep
**Context**: Adding `focus` field to `company_runs` for the startups feature.
**Issue**: Field was added to the API route and company_runs dict, but missed in `supabase_backend.py` (field mapping) and the migration used `ALTER TABLE company_runs` instead of `ALTER TABLE public.company_runs`. The `test_schema_sync.py` test would have caught both, but (a) the migration was invisible to the parser without `public.` prefix, and (b) the test wasn't run until after the UAT exposed the bug at runtime.
**Fix/Lesson**: When adding a column to any Supabase-backed table, always update three files in lockstep: (1) migration SQL with `public.` prefix, (2) `supabase_backend.py` read AND write handlers, (3) `schemas.py` Pydantic model. Run `pytest tests/test_schema_sync.py` immediately after — it takes 0.02s and catches mismatches between Python and SQL.
