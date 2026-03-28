"""Gmail integration for pipeline sync.

Searches the user's Gmail for interview-related signals using stored
Google OAuth tokens.  Multi-pass search with LLM-powered classification:

  0. LinkedIn notification emails — InMails and connection messages
  1. Known companies — messages mentioning pipeline company names
  2. New company detection — broad recruiter/interview keyword search
  3. Custom phrases — user-specified keywords/companies

Classification uses a two-pass LLM pattern when an API key is available:
  - Triage pass: batch email metadata → LLM → relevant? signal_type?
  - Deep pass: fetch full body for relevant emails → LLM → body summary
Falls back to keyword-based classification when no LLM key is provided.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

# Google API client ID for token refresh
_GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"

# LinkedIn notification sender domains
_LINKEDIN_SENDER_DOMAINS = frozenset({
    "linkedin.com",
    "messages-noreply.linkedin.com",
    "jobalerts-noreply.linkedin.com",
    "hit-reply.linkedin.com",
})

# LinkedIn subject patterns to skip (no actionable pipeline signal)
_LINKEDIN_SKIP_PATTERNS = re.compile(
    r"viewed your profile|linkedin digest|jobs you may be interested|new jobs for you|"
    r"weekly job picks|profile views|who viewed",
    re.IGNORECASE,
)

# Regex to extract company from recruiter headline in snippet (e.g. "at Acme Corp" or "@ Acme")
_LINKEDIN_COMPANY_RE = re.compile(r"(?:^|\s)(?:at|@)\s+([A-Z][A-Za-z0-9&.,'\- ]{1,50}?)(?:\s*[|·•\n,]|$)")

# LinkedIn subject patterns for recruiter name extraction
_LINKEDIN_SUBJECT_NAME_RE = re.compile(
    r"(?:(?:You have a new message from|New message from)\s+(.+?)(?:\s+on LinkedIn)?$)|"
    r"^(.+?)\s+(?:sent you a message|wants to connect|sent you an InMail)",
    re.IGNORECASE,
)

# Max body length sent to LLM deep analysis (chars)
_MAX_BODY_LENGTH = 3000


# ── Data classes ───────────────────────────────────────────────────────────────


@dataclass
class GmailSignal:
    company_name: str
    signal_type: str  # scheduling | confirmation | rejection | offer | application_status | recruiter_outreach
    subject: str
    snippet: str
    date: str
    is_new_company: bool = False
    source: str = "gmail"  # "gmail" | "linkedin"
    body_summary: str | None = None  # LLM-generated synopsis of full email body

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class _RawEmail:
    """Intermediate representation of an email before classification."""
    message_id: str
    company_name: str
    subject: str
    snippet: str
    sender: str
    date: str
    is_new_company: bool
    source: str        # "gmail" | "linkedin"
    pass_name: str     # "pass_1_known" | "pass_2_broad" | "pass_3_custom"


# ── Gmail service ──────────────────────────────────────────────────────────────


def _build_gmail_service(tokens: dict[str, str]):
    """Build an authenticated Gmail API service from stored tokens."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        token_uri=_GOOGLE_TOKEN_URI,
        # Client ID/secret not needed for token refresh via Supabase-issued tokens
        # The refresh is handled by Google's token endpoint with the refresh token alone
    )

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            log.warning("Failed to refresh Google access token; using existing token")

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# ── Keyword-based classification (fallback) ────────────────────────────────────


def _classify_signal(subject: str, snippet: str) -> str:
    """Classify an email into a signal type based on subject + snippet text.

    Used as a fallback when no LLM API key is available.
    """
    text = f"{subject} {snippet}".lower()

    rejection_words = ["unfortunately", "not moving forward", "decided not to", "other candidates", "not a fit", "regret"]
    offer_words = ["offer letter", "compensation", "start date", "we'd like to offer", "pleased to offer"]
    scheduling_words = ["schedule", "calendar invite", "interview time", "availability", "slot", "book a time"]
    confirmation_words = ["confirmed", "looking forward", "see you", "joining link", "zoom link", "meet link"]

    if any(w in text for w in offer_words):
        return "offer"
    if any(w in text for w in rejection_words):
        return "rejection"
    if any(w in text for w in scheduling_words):
        return "scheduling"
    if any(w in text for w in confirmation_words):
        return "confirmation"
    return "recruiter_outreach"


# ── Helpers ────────────────────────────────────────────────────────────────────


def _extract_company_from_email(sender: str) -> str | None:
    """Extract company name from sender email address domain."""
    match = re.search(r"@([\w.-]+)\.", sender)
    if match:
        domain = match.group(1).lower()
        # Skip generic email providers
        if domain in ("gmail", "yahoo", "hotmail", "outlook", "icloud", "protonmail", "aol"):
            return None
        return domain.replace("-", " ").title()
    return None


def _is_linkedin_sender(sender: str) -> bool:
    """Return True if the email is from a LinkedIn notification address."""
    sender_lower = sender.lower()
    return any(d in sender_lower for d in _LINKEDIN_SENDER_DOMAINS)


def _extract_linkedin_company(subject: str, snippet: str, known_companies: set[str]) -> str | None:
    """Extract company name from a LinkedIn notification email.

    Hierarchy:
      1. Known pipeline company name appearing in subject or snippet
      2. Regex match for 'at <Company>' in snippet (recruiter headline)
      3. Recruiter name from subject as placeholder '[LinkedIn: Name]'
      4. None (caller should skip)
    """
    text_lower = (subject + " " + snippet).lower()

    # 1. Known pipeline company match
    for name in known_companies:
        if name in text_lower:
            return name.title()

    # 2. Recruiter headline pattern in snippet
    match = _LINKEDIN_COMPANY_RE.search(snippet)
    if match:
        company = match.group(1).strip().rstrip(".,")
        if len(company) > 1:
            return company

    # 3. Recruiter name from subject → placeholder
    name_match = _LINKEDIN_SUBJECT_NAME_RE.search(subject)
    if name_match:
        recruiter_name = (name_match.group(1) or name_match.group(2) or "").strip()
        if recruiter_name:
            return f"[LinkedIn: {recruiter_name}]"

    return None


# ── Email body extraction ──────────────────────────────────────────────────────


def _fetch_email_body(service, message_id: str) -> str:
    """Fetch and decode the full email body text.

    Returns plain text (preferred) or HTML with tags stripped.
    Truncates to ``_MAX_BODY_LENGTH`` characters.
    """
    try:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
    except Exception as exc:
        log.warning("Failed to fetch body for message %s: %s", message_id[:8], exc)
        return ""

    payload = msg.get("payload", {})
    body_text = _extract_text_from_payload(payload)
    if body_text:
        return body_text[:_MAX_BODY_LENGTH]
    return ""


def _extract_text_from_payload(payload: dict) -> str:
    """Recursively extract text from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")

    # Simple body (no parts)
    body_data = payload.get("body", {}).get("data")
    if body_data and mime_type == "text/plain":
        return _decode_body(body_data)

    # Multipart — recurse into parts
    parts = payload.get("parts", [])
    if parts:
        # Prefer text/plain
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    return _decode_body(data)

        # Recurse into nested multipart
        for part in parts:
            if part.get("mimeType", "").startswith("multipart/"):
                result = _extract_text_from_payload(part)
                if result:
                    return result

        # Fall back to text/html with tags stripped
        for part in parts:
            if part.get("mimeType") == "text/html":
                data = part.get("body", {}).get("data")
                if data:
                    html = _decode_body(data)
                    return re.sub(r"<[^>]+>", " ", html)

    # Top-level text/html (no parts)
    if body_data and mime_type == "text/html":
        html = _decode_body(body_data)
        return re.sub(r"<[^>]+>", " ", html)

    return ""


def _decode_body(data: str) -> str:
    """Decode base64url-encoded body data."""
    try:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    except Exception:
        return ""


# ── LLM classification (two-pass) ─────────────────────────────────────────────


def _llm_triage_emails(
    raw_emails: list[_RawEmail],
    api_key: str,
    provider: str,
) -> list[dict]:
    """LLM triage pass: classify email metadata in a single batched call.

    Returns a list of dicts with keys: index, relevant (bool), signal_type, reason.
    Falls back to empty list on failure (caller should use keyword fallback).
    """
    if not raw_emails:
        return []

    from jobfinder.pipeline.reasoning import _call_anthropic, _call_gemini

    email_lines = []
    for i, email in enumerate(raw_emails):
        email_lines.append(
            f"{i + 1}. From: {email.sender[:80]} | "
            f"Subject: {email.subject[:120]} | "
            f"Date: {email.date[:30]} | "
            f"Snippet: {email.snippet[:150]}"
        )

    prompt = f"""You are filtering emails for a job seeker's application pipeline.
For each email, determine if it is related to a job application, recruiting process, or hiring pipeline.

Marketing emails, product announcements, newsletters, and promotional content are NOT relevant.
Emails about application status, interview scheduling, offers, rejections, recruiter outreach, or next steps ARE relevant.

Emails:
{chr(10).join(email_lines)}

Respond with ONLY a JSON array (no markdown fencing):
[{{"index": 1, "relevant": true, "signal_type": "application_status", "reason": "brief reason"}}, ...]

Valid signal_type values: offer, rejection, scheduling, confirmation, application_status, recruiter_outreach
For non-relevant emails, use signal_type "not_relevant"."""

    log.info("LLM triage: sending %d emails to %s", len(raw_emails), provider)

    try:
        if provider == "anthropic":
            response_text = _call_anthropic(prompt, api_key, max_tokens=1000)
        elif provider == "gemini":
            response_text = _call_gemini(prompt, api_key, max_tokens=1000)
        else:
            log.warning("LLM triage: unsupported provider %s", provider)
            return []
    except Exception as exc:
        log.warning("LLM triage call failed: %s", exc)
        return []

    # Parse JSON response
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        results = json.loads(cleaned)
        if not isinstance(results, list):
            log.warning("LLM triage: response is not a list")
            return []
        log.info(
            "LLM triage: %d/%d emails marked relevant",
            sum(1 for r in results if r.get("relevant")),
            len(raw_emails),
        )
        return results
    except json.JSONDecodeError:
        log.warning("LLM triage: failed to parse response as JSON")
        return []


def _llm_deep_analyze(
    relevant_emails: list[tuple[_RawEmail, str]],  # (email, body_text)
    pipeline_entries: list[dict],
    api_key: str,
    provider: str,
) -> list[dict]:
    """LLM deep analysis: analyze full email bodies in a single batched call.

    Returns a list of dicts with keys: index, signal_type, body_summary, confidence.
    """
    if not relevant_emails:
        return []

    from jobfinder.pipeline.reasoning import _call_anthropic, _call_gemini

    # Build entry lookup for current stage info
    stage_by_company: dict[str, str] = {}
    for e in pipeline_entries:
        name = e.get("company_name", "").lower()
        if name:
            stage_by_company[name] = e.get("stage", "not_started")

    email_blocks = []
    for i, (email, body) in enumerate(relevant_emails):
        current_stage = stage_by_company.get(email.company_name.lower(), "unknown")
        email_blocks.append(
            f"Email {i + 1} ({email.company_name}, current pipeline stage: {current_stage}):\n"
            f"Subject: {email.subject[:150]}\n"
            f"From: {email.sender[:80]}\n"
            f"Body:\n{body[:_MAX_BODY_LENGTH]}"
        )

    prompt = f"""Analyze these job-related emails from a candidate's inbox. For each email, provide:
- signal_type: the kind of update (offer, rejection, scheduling, confirmation, application_status, recruiter_outreach)
- body_summary: a 2-3 sentence synopsis capturing the key information (dates, names, next steps, action items)
- confidence: high, medium, or low

{chr(10).join(email_blocks)}

Respond with ONLY a JSON array (no markdown fencing):
[{{"index": 1, "signal_type": "scheduling", "body_summary": "...", "confidence": "high"}}, ...]"""

    log.info("LLM deep analysis: sending %d email bodies to %s", len(relevant_emails), provider)

    try:
        if provider == "anthropic":
            response_text = _call_anthropic(prompt, api_key, max_tokens=2000)
        elif provider == "gemini":
            response_text = _call_gemini(prompt, api_key, max_tokens=2000)
        else:
            return []
    except Exception as exc:
        log.warning("LLM deep analysis call failed: %s", exc)
        return []

    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        results = json.loads(cleaned)
        if not isinstance(results, list):
            return []
        signal_types = [r.get("signal_type", "?") for r in results]
        log.info("LLM deep analysis: %d results, types: %s", len(results), signal_types)
        return results
    except json.JSONDecodeError:
        log.warning("LLM deep analysis: failed to parse response as JSON")
        return []


# ── Search functions ───────────────────────────────────────────────────────────


def _search_and_collect(
    service,
    query: str,
    known_companies: set[str],
    is_new: bool,
    pass_name: str,
    max_results: int = 30,
) -> list[_RawEmail]:
    """Execute a Gmail search and collect raw email metadata (no classification)."""
    raw_emails: list[_RawEmail] = []

    log.debug("Gmail %s query: %s", pass_name, query[:200])

    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
    except Exception as exc:
        log.warning("Gmail search failed for %s [%s]: %s", pass_name, query[:60], exc)
        return []

    messages = results.get("messages", [])
    log.info("Gmail %s: %d messages returned", pass_name, len(messages))

    for msg_ref in messages:
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
                .execute()
            )
        except Exception as exc:
            log.debug("Gmail %s: failed to fetch message %s: %s", pass_name, msg_ref["id"][:8], exc)
            continue

        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "")
        sender = headers.get("from", "")
        date_str = headers.get("date", "")
        snippet = msg.get("snippet", "")

        # Skip LinkedIn emails here — handled in Pass 0
        if _is_linkedin_sender(sender):
            log.debug("Gmail %s: skipped LinkedIn email %s", pass_name, msg_ref["id"][:8])
            continue

        # Try to match to a known company
        company_name = None
        for name in known_companies:
            if name in subject.lower() or name in snippet.lower() or name in sender.lower():
                company_name = name.title()
                break

        if not company_name:
            company_name = _extract_company_from_email(sender)

        if not company_name:
            log.debug("Gmail %s: no company match for message %s (subject=%r)", pass_name, msg_ref["id"][:8], subject[:60])
            continue

        log.debug(
            "Gmail %s: matched message %s → company=%s, subject=%r",
            pass_name, msg_ref["id"][:8], company_name, subject[:60],
        )

        raw_emails.append(_RawEmail(
            message_id=msg_ref["id"],
            company_name=company_name,
            subject=subject[:200],
            snippet=snippet[:300],
            sender=sender,
            date=date_str[:30],
            is_new_company=is_new and company_name.lower() not in known_companies,
            source="gmail",
            pass_name=pass_name,
        ))

    return raw_emails


def _search_and_extract_linkedin(
    service,
    since: str,
    known_companies: set[str],
    max_results: int = 30,
) -> list[GmailSignal]:
    """Search Gmail for LinkedIn notification emails and extract recruiter signals."""
    query = (
        f"after:{since} "
        "from:(linkedin.com OR messages-noreply.linkedin.com OR "
        "jobalerts-noreply.linkedin.com OR hit-reply.linkedin.com)"
    )
    signals: list[GmailSignal] = []

    log.debug("Gmail pass_0_linkedin query: %s", query[:200])

    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
    except Exception as exc:
        log.warning("LinkedIn Gmail search failed: %s", exc)
        return []

    messages = results.get("messages", [])
    log.info("Gmail pass_0_linkedin: %d messages returned", len(messages))

    for msg_ref in messages:
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
                .execute()
            )
        except Exception:
            continue

        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "")
        sender = headers.get("from", "")
        date_str = headers.get("date", "")
        snippet = msg.get("snippet", "")

        # Verify sender is actually from LinkedIn
        if not _is_linkedin_sender(sender):
            continue

        # Skip non-actionable notification types
        if _LINKEDIN_SKIP_PATTERNS.search(subject):
            log.debug("Gmail pass_0_linkedin: skipped non-actionable %s (subject=%r)", msg_ref["id"][:8], subject[:60])
            continue

        company_name = _extract_linkedin_company(subject, snippet, known_companies)
        if not company_name:
            continue

        log.debug("Gmail pass_0_linkedin: signal from %s → company=%s", msg_ref["id"][:8], company_name)

        signals.append(
            GmailSignal(
                company_name=company_name,
                signal_type="recruiter_outreach",
                subject=subject[:200],
                snippet=snippet[:300],
                date=date_str[:30],
                is_new_company=company_name.lower() not in known_companies,
                source="linkedin",
            )
        )

    return signals


# ── Classification pipeline ───────────────────────────────────────────────────


def _classify_with_llm(
    raw_emails: list[_RawEmail],
    service,
    pipeline_entries: list[dict],
    api_key: str,
    provider: str,
) -> list[GmailSignal]:
    """Two-pass LLM classification: triage metadata, then deep-analyze bodies.

    Falls back to keyword classification if LLM calls fail.
    """
    if not raw_emails:
        return []

    # ── Pass 1: Triage (cheap — metadata only) ────────────────────────────
    triage_results = _llm_triage_emails(raw_emails, api_key, provider)

    if not triage_results:
        log.info("LLM triage returned nothing; falling back to keyword classification")
        return _classify_with_keywords(raw_emails)

    # Build index→triage result lookup
    triage_by_index: dict[int, dict] = {}
    for r in triage_results:
        idx = r.get("index")
        if isinstance(idx, int):
            triage_by_index[idx] = r

    # Split into relevant and non-relevant
    relevant_indices: list[int] = []
    signals: list[GmailSignal] = []

    for i, email in enumerate(raw_emails):
        triage = triage_by_index.get(i + 1, {})  # 1-indexed in prompt
        is_relevant = triage.get("relevant", False)

        if is_relevant:
            relevant_indices.append(i)
        else:
            log.debug(
                "LLM triage: email %s (%s) marked not relevant: %s",
                email.message_id[:8], email.company_name, triage.get("reason", "no reason"),
            )

    log.info("LLM triage: %d/%d emails relevant, proceeding to deep analysis", len(relevant_indices), len(raw_emails))

    if not relevant_indices:
        return []

    # ── Pass 2: Deep analysis (expensive — full body) ─────────────────────
    relevant_with_body: list[tuple[_RawEmail, str]] = []
    for i in relevant_indices:
        email = raw_emails[i]
        body = _fetch_email_body(service, email.message_id)
        if body:
            relevant_with_body.append((email, body))
            log.debug("Fetched body for %s (%s): %d chars", email.message_id[:8], email.company_name, len(body))
        else:
            # No body fetched — still include with snippet as fallback
            relevant_with_body.append((email, email.snippet))
            log.debug("No body for %s (%s), using snippet", email.message_id[:8], email.company_name)

    deep_results = _llm_deep_analyze(relevant_with_body, pipeline_entries, api_key, provider)

    # Build index→deep result lookup
    deep_by_index: dict[int, dict] = {}
    for r in deep_results:
        idx = r.get("index")
        if isinstance(idx, int):
            deep_by_index[idx] = r

    # Build final signals from deep analysis
    for j, (email, _body) in enumerate(relevant_with_body):
        deep = deep_by_index.get(j + 1, {})
        triage = triage_by_index.get(relevant_indices[j] + 1, {})

        signal_type = deep.get("signal_type") or triage.get("signal_type") or "recruiter_outreach"
        body_summary = deep.get("body_summary")

        signals.append(GmailSignal(
            company_name=email.company_name,
            signal_type=signal_type,
            subject=email.subject,
            snippet=email.snippet,
            date=email.date,
            is_new_company=email.is_new_company,
            source=email.source,
            body_summary=body_summary,
        ))

    return signals


def _classify_with_keywords(raw_emails: list[_RawEmail]) -> list[GmailSignal]:
    """Keyword-based classification fallback (no LLM needed)."""
    signals: list[GmailSignal] = []
    for email in raw_emails:
        signal_type = _classify_signal(email.subject, email.snippet)
        signals.append(GmailSignal(
            company_name=email.company_name,
            signal_type=signal_type,
            subject=email.subject,
            snippet=email.snippet,
            date=email.date,
            is_new_company=email.is_new_company,
            source=email.source,
        ))
    return signals


# ── Main entry point ──────────────────────────────────────────────────────────


def scan_gmail(
    tokens: dict[str, str],
    pipeline_entries: list[dict],
    lookback_days: int = 3,
    custom_phrases: list[str] | None = None,
    api_key: str | None = None,
    provider: str | None = None,
) -> list[GmailSignal]:
    """Search Gmail for interview-related signals.

    When ``api_key`` and ``provider`` are given, uses LLM two-pass classification
    (triage + deep body analysis).  Falls back to keyword classification otherwise.

    Returns a list of GmailSignal objects (serializable via .to_dict()).
    """
    try:
        service = _build_gmail_service(tokens)
    except Exception as exc:
        log.error("Failed to build Gmail service: %s", exc)
        return []

    since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y/%m/%d")

    # Build known company names set (lowercase for matching)
    known_companies = {e.get("company_name", "").lower() for e in pipeline_entries}
    known_companies.discard("")

    log.info(
        "Gmail sync: %d known companies, lookback=%d days (since %s), llm=%s",
        len(known_companies), lookback_days, since,
        provider if api_key else "none (keyword fallback)",
    )

    # ── Pass 0: LinkedIn notification emails (unchanged — always keyword) ─
    linkedin_signals = _search_and_extract_linkedin(service, since, known_companies)
    linkedin_companies = {s.company_name.lower() for s in linkedin_signals}

    # ── Pass 1-3: Collect raw emails ──────────────────────────────────────
    all_raw: list[_RawEmail] = []
    seen_message_ids: set[str] = set()

    # Pass 1: Known companies
    if known_companies:
        company_names = list(known_companies)
        for i in range(0, len(company_names), 20):
            batch = company_names[i : i + 20]
            or_clause = " OR ".join(f'"{name}"' for name in batch)
            query = f"after:{since} ({or_clause})"
            raw = _search_and_collect(service, query, known_companies, is_new=False, pass_name="pass_1_known")
            for email in raw:
                # Skip if already captured as LinkedIn signal or duplicate
                if email.company_name.lower() not in linkedin_companies and email.message_id not in seen_message_ids:
                    all_raw.append(email)
                    seen_message_ids.add(email.message_id)

    # Pass 2: Broad recruiter signal search
    broad_query = (
        f"after:{since} "
        '(recruiter OR "hiring manager" OR "next steps" OR "move forward" '
        'OR "schedule a call" OR interview OR screening OR application OR offer '
        'OR "excited to connect" OR "opportunity at")'
    )
    broad_raw = _search_and_collect(service, broad_query, known_companies, is_new=True, pass_name="pass_2_broad")

    existing_names = {e.company_name.lower() for e in all_raw} | {s.company_name.lower() for s in linkedin_signals}
    for email in broad_raw:
        if (email.company_name.lower() not in existing_names
                and email.company_name.lower() not in known_companies
                and email.message_id not in seen_message_ids):
            all_raw.append(email)
            seen_message_ids.add(email.message_id)
            existing_names.add(email.company_name.lower())

    # Pass 3: Custom phrases
    phrases = [p.strip() for p in (custom_phrases or []) if p.strip()]
    if phrases:
        or_clause = " OR ".join(f'"{p}"' for p in phrases)
        phrase_query = f"after:{since} ({or_clause})"
        phrase_raw = _search_and_collect(service, phrase_query, known_companies, is_new=True, pass_name="pass_3_custom")
        for email in phrase_raw:
            if (email.company_name.lower() not in existing_names
                    and email.company_name.lower() not in known_companies
                    and email.message_id not in seen_message_ids):
                all_raw.append(email)
                seen_message_ids.add(email.message_id)
                existing_names.add(email.company_name.lower())

    log.info("Gmail sync: collected %d raw emails across passes 1-3", len(all_raw))

    # ── Classify ──────────────────────────────────────────────────────────
    if api_key and provider and all_raw:
        classified_signals = _classify_with_llm(all_raw, service, pipeline_entries, api_key, provider)
    elif all_raw:
        log.info("Gmail sync: no LLM key, using keyword classification for %d emails", len(all_raw))
        classified_signals = _classify_with_keywords(all_raw)
    else:
        classified_signals = []

    signals = linkedin_signals + classified_signals

    log.info(
        "Gmail sync complete: %d total signals (%d LinkedIn, %d classified)",
        len(signals), len(linkedin_signals), len(classified_signals),
    )

    return signals
