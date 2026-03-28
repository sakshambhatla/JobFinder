# jobfinder/pipeline — Claude Context

Pipeline sync module: scans Gmail + Google Calendar for job interview signals, uses LLM (or rule-based fallback) to reason about stage transitions, and presents structured suggestions for user review. Also provides LLM-powered offer evaluation.

## File Map

```
pipeline/
  __init__.py         # Module marker
  gmail.py            # Gmail API scanner — 4-pass search + LLM two-pass classification
  calendar.py         # Google Calendar scanner — interview detection + company matching
  reasoning.py        # LLM reasoning + rule_based_suggestions() + merge_rule_based_for_uncovered()
  offer_analysis.py   # LLM-powered offer evaluation across 10 weighted dimensions
```

## Architecture

### Signal Extraction Layer

**`gmail.py`** — `scan_gmail(tokens, entries, lookback_days=3, custom_phrases=None, api_key=None, provider=None) -> list[GmailSignal]`

Four search passes, run in order:

- **Pass 0** (`_search_and_extract_linkedin`): LinkedIn notification emails — fixed sender domains, always keyword-based (no LLM). Skips non-actionable notifications (job digests, profile views). Extracts company via: known pipeline name match → `"at <Company>"` regex in snippet → recruiter name placeholder `[LinkedIn: Name]`. Results excluded from passes 1–3.
- **Pass 1**: Known pipeline companies — quoted name search, skips LinkedIn senders.
- **Pass 2**: Broad recruiter/interview keyword search — new companies only (skips already-seen).
- **Pass 3**: Custom phrases — searches user-supplied keywords (passed via `custom_phrases` param or API request body). New companies only.

Passes 1–3 deduplicate by Gmail message ID before classification.

**Classification** (passes 1–3 only):
- **With LLM** (`api_key` + `provider` provided): two-pass pattern
  - Triage pass: batch email metadata → LLM → `relevant? signal_type?`
  - Deep pass: fetch full body for relevant emails (up to 3000 chars) → LLM → `signal_type` + `body_summary`
  - Falls back to keyword classification if LLM triage returns nothing
- **Without LLM**: keyword-based fallback (`_classify_with_keywords`)

`GmailSignal` fields: `company_name`, `signal_type`, `subject`, `snippet`, `date`, `is_new_company`, `source` (`"gmail"` | `"linkedin"`), `body_summary` (LLM-generated synopsis, `None` on keyword path).

Signal types: `offer`, `rejection`, `scheduling`, `confirmation`, `application_status`, `recruiter_outreach`

**`calendar.py`** — `scan_calendar(tokens, entries, past_days=3, future_days=7) -> list[CalendarSignal]`
- Fetches events from primary calendar
- Filters by 16 interview keywords in title/description
- Matches events to pipeline companies by name / organizer email domain / title patterns
- Classifies: `upcoming_interview`, `completed_interview`, `scheduled`

### Reasoning Layer (swappable)

**`reasoning.py`** has three paths:

1. **LLM path**: `reason_pipeline(entries, gmail_signals, calendar_signals, api_key, model_provider, model_name=None) -> ReasoningResult`
   - Builds prompt with current pipeline state + signals + `STAGE_TRANSITION_RULES` (includes LinkedIn-specific rules)
   - Calls Anthropic or Gemini (`_call_anthropic()` / `_call_gemini()`)
   - Parses JSON → `ReasoningResult`; fuzzy-matches company names to entry IDs (normalized suffix strip + substring containment)
   - `STAGE_TRANSITION_RULES` LinkedIn addendum: LinkedIn signals → suggest `"outreach"` stage (not `"recruiter"`); resolve `[LinkedIn: Name]` placeholders to real company name if extractable from snippet

2. **Rule-based fallback**: `rule_based_suggestions(gmail_signals, calendar_signals, entries) -> ReasoningResult`
   - Maps signal types to stages/badges via lookup tables (`_SIGNAL_STAGE_MAP`, `_SIGNAL_BADGE_MAP`)
   - Deduplicates: keeps highest-priority signal per company (offer > rejection > scheduling > confirmation > recruiter_outreach)
   - No LLM needed

3. **Hybrid merge**: `merge_rule_based_for_uncovered(llm_result, gmail_signals, calendar_signals, entries) -> ReasoningResult`
   - Computes which companies LLM already covered
   - Runs rule-based on the full signal set
   - Appends rule-based results only for companies the LLM did NOT address

**All three paths return `ReasoningResult`** — the sync endpoint doesn't care which path was used.

### Offer Analysis (`offer_analysis.py`)

**`analyze_offer(company_name, role_title, personal_context, api_key, model_provider="anthropic", model_name=None) -> dict`**
- Prompts LLM to research company from public sources (Glassdoor, Blind, LinkedIn, Crunchbase, news)
- Scores 10 dimensions (1–5 each); dimensions 1–4 weighted 1.5x, 5–10 weighted 1.0x
- Parser recomputes `weighted_score` and `raw_average` from the returned dimensions for accuracy (ignores LLM-computed values)
- Called from `POST /pipeline/offer-analyses`

Dimensions: business trajectory, financial stability, management quality, engineering culture (1.5x each) · work-life balance, compensation, career growth, mission clarity, org health, location fit (1.0x each)

Output keys: `dimensions[]` (name/score/weight/rationale/flag), `weighted_score`, `raw_average`, `verdict`, `key_question`, `flags` ({red/yellow/green counts})

### Sync API (`api/routes/pipeline.py`)

- `POST /pipeline/sync` — orchestrates: load entries → scan Gmail/Calendar → try `reason_pipeline()` across all `SUPPORTED_PROVIDERS` → `merge_rule_based_for_uncovered()` to fill gaps → fall back to pure `rule_based_suggestions()` if no LLM key → return signals + suggestions
- `POST /pipeline/sync/apply` — accepts selected suggestions, creates/updates `PipelineEntry` records + `PipelineUpdate` changelog entries
- `POST /pipeline/offer-analyses` — calls `analyze_offer()` and persists to `offer_analyses.json`

### Frontend View Model: JobUpdate

**`JobUpdate`** (defined in `ui/src/lib/api.ts`) is a frontend-only view model for the 3-column sync review modal. Built from `PipelineSuggestion` + signal data via `buildJobUpdates()` in `PipelineSyncModal.tsx`.

Fields: `source`, `company_name`, `stage`, `badge`, `next_action`, `note`, `recommendation` (`"add"` | `"update"` | `"ignore"`)

### Data Flow

```
User clicks "Refresh Pipeline"
    ↓
POST /pipeline/sync
    ├── scan_gmail() → GmailSignal[]          (Pass 0: LinkedIn; Passes 1–3: LLM or keyword)
    ├── scan_calendar() → CalendarSignal[]
    └── reason_pipeline() → ReasoningResult
        └── merge_rule_based_for_uncovered() fills gaps
        (or rule_based_suggestions() if no LLM key)
    ↓
Frontend: buildJobUpdates() converts to JobUpdate[]
    ↓
3-column modal: Signal | Recommendation (dropdown) | Pipeline Entry Preview
    ↓
User reviews, overrides recommendations, clicks Apply
    ↓
POST /pipeline/sync/apply
    ├── Updates existing PipelineEntry records
    ├── Creates new PipelineEntry records
    └── Generates PipelineUpdate changelog entries
    ↓
Kanban board re-fetches → new/updated cards appear
```

## Key Patterns

- **Provider-agnostic LLM**: sync endpoint iterates `SUPPORTED_PROVIDERS` from `config.py`, not hardcoded provider names
- **Graceful degradation**: no Google tokens → skip scans; no LLM key → rule-based fallback; no signals → empty result; LLM triage returns nothing → keyword fallback for that batch
- **LLM two-pass Gmail**: triage pass (cheap, metadata only) → deep pass (expensive, full body); each pass falls back independently
- **LinkedIn signal isolation**: Pass 0 runs before passes 1–3; LinkedIn signals bypass LLM classification entirely (always `source="linkedin"`, always `signal_type="recruiter_outreach"`)
- **Hybrid merge**: after LLM reasoning, `merge_rule_based_for_uncovered()` fills gaps for any signals the LLM skipped
- **Two-step apply**: suggestions are never auto-applied — user reviews in modal first
- **Signal dedup**: `rule_based_suggestions()` keeps highest-priority signal per company; passes 1–3 dedup by message ID
- **Token refresh**: Gmail/Calendar modules auto-refresh expired Google access tokens
- **Score recomputation**: `offer_analysis.py` parser recomputes `weighted_score` from parsed dimensions, not from LLM-supplied value, for numerical accuracy

## Adding a New Signal Source

1. Create `pipeline/<source>.py` with a `scan_<source>(tokens, entries) -> list[<Source>Signal]` function
2. Add the scan call in `POST /pipeline/sync` (wrap in `asyncio.to_thread()`)
3. Pass signals to `reason_pipeline()` and `rule_based_suggestions()`
4. Update `buildJobUpdates()` in `PipelineSyncModal.tsx` to handle the new signal type

## Modifying the Conversion Layer

The `buildJobUpdates()` function in `PipelineSyncModal.tsx` is the conversion layer from backend `PipelineSuggestion` → frontend `JobUpdate`. To swap the strategy:
- Modify `buildJobUpdates()` for frontend-only changes
- Or modify `reasoning.py` to change how suggestions are generated
- The `JobUpdate` interface is the stable contract between conversion and display
