---
name: uat
description: >
  Run a comprehensive User Acceptance Test of the full managed-mode workflow.
  Starts a UAT UI server on port 5180 (shares the user's API server on :8000),
  logs in, uploads a test resume, stores a Gemini API key,
  discovers companies (5), and discovers roles (semantic filter, cached) —
  verifying each step via the UI with screenshots as proof.
  Use this skill whenever the user says "do a UAT", "run UAT", "comprehensive check",
  "end-to-end test", "managed mode test", or any similar phrase about running
  the full managed-mode acceptance test.
---

# UAT — Managed-Mode Acceptance Test

End-to-end test of the full VerdantMe managed-mode workflow against live Supabase.

The UAT runs on a **dedicated UI port (5180)** so it never conflicts with the user's
own dev instance on port 5173. It shares the user's API server on port 8000.

## Pre-flight (Step 0)

Source `~/.env` and check that all required env vars are set. Run this in Bash:

```bash
source ~/.env 2>/dev/null
for var in VERDANTME_TEST_EMAIL VERDANTME_TEST_PASSWORD GEMINI_API_KEY SUPABASE_URL SUPABASE_PUBLISHABLE_KEY; do
  if [ -z "${!var}" ]; then echo "MISSING: $var"; else echo "OK: $var"; fi
done
```

Also verify the test resume exists:

```bash
test -f /Users/sakshambhatla/workplace/JobFinder/tests/fixtures/uat_resume.txt && echo "OK: uat_resume.txt" || echo "MISSING: uat_resume.txt"
```

If anything is missing, report and abort. Do NOT proceed.

## Step 1 — Start servers

The UAT assumes the user's API server is already running on port 8000.
Check that it's reachable:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/resume
```

- If the API returns 200 or 404, it's running — proceed.
- If the curl fails (connection refused), tell the user:
  "The API server on :8000 is not running. Please start it with `jobfinder serve --host 0.0.0.0 --port 8000 --reload` or let me start it."
  If the user agrees, use `preview_start(name="api-dev")` and check `preview_logs` for "Application startup complete".

Start only the UAT UI server:
- `preview_start(name="uat-ui-dev")` — port 5180 (Vite frontend, dedicated for UAT)

Check `preview_logs` on the UI server for startup confirmation ("ready" or "Local:").

## Step 2 — Navigate & select "Run Managed"

Using the `uat-ui-dev` server's preview tools:

1. Clear stale mode: `preview_eval` → `localStorage.removeItem('verdantme-mode'); window.location.reload()`
2. Wait for page to settle, then `preview_screenshot` to confirm the mode selection page (two cards: "Run Local" and "Run Managed")
3. Click the "Run Managed" card. It's the **second** `<button>` element on the page. Use `preview_eval`:
   ```javascript
   document.querySelectorAll('button')[1].click()
   ```

## Step 3 — Login

1. `preview_snapshot` to confirm the login form (email input, password input, Sign In button)
2. Read credentials from env vars using Bash: `source ~/.env && echo $VERDANTME_TEST_EMAIL` and `source ~/.env && echo $VERDANTME_TEST_PASSWORD`
3. `preview_fill` the email input (selector: `input[type="email"]`) with the email
4. `preview_fill` the password input (selector: `input[type="password"]`) with the password
5. Click Sign In: `preview_eval` → `document.querySelector('button[type="submit"]') ? document.querySelector('button[type="submit"]').click() : document.querySelectorAll('button').forEach(b => { if (b.textContent.includes('Sign in')) b.click() })`
6. Wait ~2 seconds, then `preview_screenshot`
7. **Verify**: main app shell visible (tabs: "Upload Resume", "Discover Companies", "Discover Roles"). If an error message appears, capture it and abort.

## Step 4 — Upload test resume

1. `preview_snapshot` to confirm the ResumeTab is visible (drop zone with "Drop your resume here")
2. First, delete any existing resumes by clicking their trash buttons:
   ```javascript
   // Find and click all remove-resume buttons (they have empty text content and are after the tab buttons)
   const btns = [...document.querySelectorAll('button')];
   const removeBtns = btns.filter(b => b.textContent.trim() === '' && b.closest('[role="tabpanel"]'));
   removeBtns.forEach(b => b.click());
   ```
   Wait 1 second between deletions if multiple exist.
3. Read the resume file content via Bash:
   ```bash
   cat /Users/sakshambhatla/workplace/JobFinder/tests/fixtures/uat_resume.txt
   ```
4. Upload via `preview_eval` — inject the file content into the hidden input:
   ```javascript
   (function() {
     const content = `<PASTE RESUME CONTENT HERE>`;
     const file = new File([content], 'uat_resume.txt', { type: 'text/plain' });
     const input = document.querySelector('input[type="file"]');
     const dt = new DataTransfer();
     dt.items.add(file);
     input.files = dt.files;
     input.dispatchEvent(new Event('change', { bubbles: true }));
   })()
   ```
5. Wait ~3 seconds, then `preview_snapshot`
6. **Verify**: a parsed resume card appears showing "uat_resume.txt" with titles and skills badges
7. Check `preview_console_logs(level="error")` and `preview_logs(serverId=api, level="error")` for errors
8. `preview_screenshot` as proof

## Step 5 — Store Gemini API key

1. Read the key from env: `source ~/.env && echo $GEMINI_API_KEY` (via Bash)
2. Click profile menu: `preview_eval` → `document.querySelector('[aria-label="Profile menu"]').click()`
3. Wait ~500ms, then `preview_snapshot` to find the dropdown items
4. Click "API Keys" menu item: find the dropdown item containing "API Keys" text and click it
5. Wait ~500ms, then `preview_snapshot` to confirm the ApiKeysDialog opened
6. Find the Gemini key input. It's an `input[type="password"]` inside the Gemini provider row (the second provider row, or the one near text "Google Gemini"). Fill it with `preview_fill` using the appropriate selector.
7. Click the "Save" button next to the Gemini input
8. Wait ~3 seconds for validation + storage
9. `preview_snapshot` — **verify**: a green "Stored" badge appears next to the Gemini row
10. Close the dialog (press Escape or click outside)
11. `preview_screenshot` as proof

## Step 6 — Discover 5 companies

1. Click the "Discover Companies" tab: `preview_eval` →
   ```javascript
   document.querySelectorAll('[role="tab"]')[1].click()
   ```
2. Wait ~500ms, then `preview_snapshot` to confirm CompaniesTab
3. Set max_companies to 5: `preview_fill(selector="#max-companies", value="5")`
   - If the fill doesn't clear the existing value, use `preview_eval` first:
     ```javascript
     const el = document.querySelector('#max-companies');
     el.value = '';
     el.dispatchEvent(new Event('input', { bubbles: true }));
     ```
     Then `preview_fill`.
4. Confirm provider is "gemini" (it's the default). If not, use `preview_fill(selector="#provider", value="gemini")`
5. Click "Discover Companies" button: find the button with text "Discover Companies" and click it
6. **Poll for completion** (max 120 seconds, check every 10 seconds):
   - `preview_snapshot` — look for:
     - Success: a company table appears (text like "Companies" with numbered rows)
     - Failure: an error message (red text, "Error", "Failed")
     - Still running: spinner or "Discovering..." text
7. Check `preview_console_logs(level="error")` and `preview_logs(serverId=api, level="error")`
8. `preview_screenshot` as proof — capture the company table

## Step 7 — Discover roles

1. Click the "Discover Roles" tab: `preview_eval` →
   ```javascript
   document.querySelectorAll('[role="tab"]')[2].click()
   ```
2. Wait ~500ms, then `preview_snapshot` to confirm RolesTab
3. The "Last Discovery Run" company source should already be selected (default)
4. Set a title filter to activate filter strategy options:
   - Find the title filter input (labeled "Job Title") and fill with "Engineer"
5. Select "Semantic" filter strategy: click the button/radio with text "Semantic"
6. Check "Use cached results": find and check the checkbox near "Use cached" text
7. Click "Discover Roles" button
8. **Poll for completion** (max 300 seconds, check every 15 seconds):
   - `preview_snapshot` — look for:
     - Success: a roles table with rows (Score, Company, Title columns)
     - Failure: an error message
     - Still running: spinner or progress text
9. Check `preview_console_logs(level="error")` and `preview_logs(serverId=api, level="error")`
10. `preview_screenshot` as proof — capture the roles table

## Step 8 — Report

Output a final summary table:

```
## UAT Results

| Step | Status | Details |
|------|--------|---------|
| Servers | .../... | api :8000 (user's), uat-ui :5180 |
| Login | .../... | Signed in as <email> |
| Resume upload | .../... | N skills, M titles parsed |
| API key | .../... | Gemini key stored |
| Companies | .../... | N companies discovered |
| Roles | .../... | N roles found, M after filter |

Verdict: All UAT steps passed / Step X failed: <details>
```

## Important notes

- **Parallel-safe**: UAT runs on port 5180, never conflicts with the user's dev instance on 5173.
- **Shared API**: UAT reuses the user's API server on port 8000. The API must be running before starting the UAT.
- **CORS**: `~/.env` has `CORS_ORIGINS=http://localhost:5173,http://localhost:5180` so both ports are always allowed.
- **Fail-fast**: if any step fails, capture screenshot + console/server logs and STOP. Do not continue to later steps since they depend on earlier ones.
- **No cleanup**: UAT data persists for manual inspection. Re-runs overwrite.
- **Polling, not sleeping**: always check `preview_snapshot` for success/failure indicators rather than using fixed waits.
- **Credentials from env vars only**: never hardcode emails, passwords, or API keys in the skill. Always `source ~/.env` before reading env vars in Bash commands.
