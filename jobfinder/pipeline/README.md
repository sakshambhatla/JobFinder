# jobfinder/pipeline

Automated job-search pipeline sync. Scans Gmail and Google Calendar for interview signals, reasons about stage transitions using an LLM (with a rule-based fallback), and surfaces structured suggestions for the user to review before applying. Also provides LLM-powered offer evaluation.

---

## Module Structure

| File | Responsibility |
|------|----------------|
| `gmail.py` | 4-pass Gmail search + LLM two-pass classification (triage → deep body analysis) |
| `calendar.py` | Google Calendar interview event detection and company matching |
| `reasoning.py` | LLM reasoning, rule-based fallback, and hybrid merge for pipeline suggestions |
| `offer_analysis.py` | 10-dimension weighted offer evaluation via LLM |

---

## Data Flow

```
User clicks "Refresh Pipeline"
         │
         ▼
POST /pipeline/sync
         │
         ├─► scan_gmail()            ─► GmailSignal[]
         │    Pass 0: LinkedIn notifications (keyword, always)
         │    Pass 1: Known pipeline companies (LLM or keyword)
         │    Pass 2: Broad recruiter keywords (LLM or keyword)
         │    Pass 3: Custom phrases      (LLM or keyword)
         │
         ├─► scan_calendar()         ─► CalendarSignal[]
         │    Upcoming + recent interview events
         │
         └─► reason_pipeline()       ─► ReasoningResult
              └─► merge_rule_based_for_uncovered()  (fills LLM gaps)
              (or rule_based_suggestions() if no LLM key)
         │
         ▼
Frontend: buildJobUpdates() → JobUpdate[] (3-column review modal)
         │
         ▼
User reviews suggestions, overrides as needed, clicks Apply
         │
         ▼
POST /pipeline/sync/apply
    Updates PipelineEntry records + PipelineUpdate changelog
         │
         ▼
Kanban board re-fetches → cards updated
```

---

## Key Entry Points

### Gmail scan

```python
from jobfinder.pipeline.gmail import scan_gmail

signals = scan_gmail(
    tokens={"access_token": "...", "refresh_token": "..."},
    pipeline_entries=[...],   # current pipeline for company matching
    lookback_days=3,          # 1–14
    custom_phrases=["Acme", "series B startup"],  # optional extra keywords
    api_key="sk-...",         # optional; enables LLM classification
    provider="anthropic",     # "anthropic" | "gemini"
)
```

### Calendar scan

```python
from jobfinder.pipeline.calendar import scan_calendar

signals = scan_calendar(
    tokens={"access_token": "...", "refresh_token": "..."},
    pipeline_entries=[...],
    past_days=3,
    future_days=7,
)
```

### Pipeline reasoning

```python
from jobfinder.pipeline.reasoning import (
    reason_pipeline,
    rule_based_suggestions,
    merge_rule_based_for_uncovered,
)

# LLM path
result = reason_pipeline(entries, gmail_signals, calendar_signals, api_key, model_provider)

# Fill gaps the LLM missed
result = merge_rule_based_for_uncovered(result, gmail_signals, calendar_signals, entries)

# Or: fully rule-based (no LLM)
result = rule_based_suggestions(gmail_signals, calendar_signals, entries)
```

### Offer analysis

```python
from jobfinder.pipeline.offer_analysis import analyze_offer

analysis = analyze_offer(
    company_name="Acme Corp",
    role_title="Staff Engineer",      # optional
    personal_context="I have a mortgage and prefer stability over upside.",
    api_key="sk-...",
    model_provider="anthropic",       # "anthropic" | "gemini"
)
# Returns: dimensions[], weighted_score, raw_average, verdict, key_question, flags
```

---

## Signal Types

| Type | Meaning |
|------|---------|
| `offer` | Offer letter / compensation / start date mentioned |
| `rejection` | "Not moving forward", "decided not to proceed" |
| `scheduling` | Interview time requested or slot proposed |
| `confirmation` | Interview confirmed — Zoom link, "see you Thursday" |
| `application_status` | ATS status update (e.g., "application under review") |
| `recruiter_outreach` | Cold outreach, InMail, LinkedIn message |

`source` field: `"gmail"` (regular email) or `"linkedin"` (LinkedIn notification).

---

## Stage Transition Rules

| Transition | Trigger |
|------------|---------|
| `not_started` → `outreach` | First LinkedIn InMail or cold recruiter email (no call scheduled yet) |
| `not_started` → `recruiter` | Recruiter outreach with call already scheduled |
| `outreach` → `recruiter` | Initial outreach turns into a scheduled recruiter call |
| `recruiter` → `hm_screen` | Recruiter screen completed, advancing to hiring manager |
| `hm_screen` → `onsite` | Panel / full onsite loop confirmed |
| any → `blocked` | ATS rejection, no open roles, hiring freeze (never had interview) |
| any → `rejected` | Formal rejection after an actual interview |

**LinkedIn signals** always suggest `outreach` stage (not `recruiter` — that implies a call has occurred). Company name is resolved from snippet if signal uses a `[LinkedIn: Name]` placeholder.

## Badge Rules

| Badge | Meaning |
|-------|---------|
| `sched` | Upcoming confirmed interview with a specific date/time |
| `done` | Completed a step today, awaiting next |
| `await` | Waiting on a response, no action needed |
| `new` | Just entered the pipeline |
| `panel` | Full panel or onsite loop confirmed |
| _(null)_ | No active status |

---

## Offer Evaluation Dimensions

Dimensions 1–4 are weighted **1.5x**; dimensions 5–10 are **1.0x**.

| # | Dimension | Focus |
|---|-----------|-------|
| 1 | Business trajectory | Growth, funding, headcount trends |
| 2 | Financial stability & runway | Job safety over 12–24 months |
| 3 | Management quality | Leadership competence and people treatment |
| 4 | Engineering culture | Talent density, blogs, open source |
| 5 | Work-life balance | WLB ratings, on-call burden, flexibility |
| 6 | Compensation & equity | Total package competitiveness |
| 7 | Career growth | Promotions, scope, brand for future roles |
| 8 | Mission & product clarity | Value proposition, defensibility |
| 9 | Org health & stability | Reorgs, manager turnover, team structure |
| 10 | Location & logistics | Commute, in-office days, timezone |

`weighted_score` = (Σ score × weight) / (Σ weights). Always recomputed from returned dimensions.

---

## Adding a New Signal Source

1. Create `pipeline/<source>.py` with `scan_<source>(tokens, entries) -> list[<Source>Signal]`
2. Add the scan call in `POST /pipeline/sync` in `api/routes/pipeline.py` (wrap in `asyncio.to_thread()`)
3. Pass its signals to `reason_pipeline()` and `rule_based_suggestions()`
4. Update `buildJobUpdates()` in `ui/src/components/PipelineSyncModal.tsx` to handle the new signal type

---

## Graceful Degradation

| Missing | Behavior |
|---------|----------|
| No Google tokens | Gmail/Calendar scans skipped; returns empty signals |
| No LLM API key | Rule-based fallback used for all suggestions |
| LLM triage returns nothing | Keyword classification used for that email batch |
| LLM reasoning returns no suggestions | `merge_rule_based_for_uncovered()` fills from rules |
| Offer analysis LLM fails | `analyze_offer()` raises; API layer returns 500 |
