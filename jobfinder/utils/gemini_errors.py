"""Utilities for parsing and formatting Gemini 429 RESOURCE_EXHAUSTED errors."""
from __future__ import annotations

import ast
import re


# ── Metric → human label ─────────────────────────────────────────────────────
_METRIC_LABELS: dict[str, str] = {
    "free_tier_requests": "request count",
    "generate_content_free_tier_requests": "request count",
    "free_tier_input_token_count": "token count",
    "generate_content_free_tier_input_token_count": "token count",
}

_RETRY_INFO_TYPE = "type.googleapis.com/google.rpc.RetryInfo"
_QUOTA_FAILURE_TYPE = "type.googleapis.com/google.rpc.QuotaFailure"


def _parse_body(exc: Exception) -> dict:
    """Extract the structured error dict from a Gemini ClientError.

    The string repr of ClientError looks like:
        "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, ...}}"
    We try ast.literal_eval on the dict portion.  Returns {} on failure.
    """
    try:
        detail = str(exc)
        brace = detail.index("{")
        return ast.literal_eval(detail[brace:])
    except Exception:
        return {}


def _metric_label(metric: str) -> str:
    # Try suffix match against known labels
    for key, label in _METRIC_LABELS.items():
        if metric.endswith(key):
            return label
    # Fall back: last path segment, replace underscores
    return metric.rsplit("/", 1)[-1].replace("_", " ")


def _window_label(quota_id: str) -> str:
    ql = quota_id.lower()
    if "perday" in ql or "per_day" in ql:
        return "daily"
    if "perminute" in ql or "per_minute" in ql:
        return "per-minute"
    return "quota"


def format_gemini_429(
    exc: Exception, model_name: str
) -> tuple[str, bool, int]:
    """Parse a Gemini 429 ClientError and return a human-readable summary.

    Returns:
        summary      — multi-line string to print to the console
        is_daily     — True if any violation is a daily quota (no point retrying)
        retry_wait   — seconds to wait before retrying (API value + 5s buffer)
    """
    body = _parse_body(exc)
    error = body.get("error", {})
    details = error.get("details", [])

    violations: list[dict] = []
    retry_delay_secs = 0

    for entry in details:
        t = entry.get("@type", "")
        if t == _RETRY_INFO_TYPE:
            raw_delay = entry.get("retryDelay", "0s")
            m = re.match(r"([\d.]+)", str(raw_delay))
            if m:
                retry_delay_secs = int(float(m.group(1))) + 5
        elif t == _QUOTA_FAILURE_TYPE:
            violations.extend(entry.get("violations", []))

    if retry_delay_secs == 0:
        # Fall back to regex on the raw message if RetryInfo wasn't present
        m = re.search(r"retry in ([\d.]+)s", str(exc).lower())
        retry_delay_secs = int(float(m.group(1))) + 5 if m else 65

    is_daily = any("perday" in v.get("quotaId", "").lower() for v in violations)

    if not violations:
        # Parsing failed — return a plain fallback
        summary = f"  Rate limit ({model_name}): quota exceeded."
        return summary, is_daily, retry_delay_secs

    lines = [f"  Rate limit ({model_name}, free tier):"]
    for v in violations:
        metric = _metric_label(v.get("quotaMetric", ""))
        window = _window_label(v.get("quotaId", ""))
        limit = v.get("quotaValue", "?")
        lines.append(f"    • {metric} – {window} limit: {limit} · retry in {retry_delay_secs}s")

    return "\n".join(lines), is_daily, retry_delay_secs


def log_gemini_429(
    exc: Exception,
    model_name: str,
    debug: bool,
    console: object,
) -> tuple[str, bool, int]:
    """Format and print a Gemini 429 error.  Returns (summary, is_daily, retry_wait)."""
    summary, is_daily, retry_wait = format_gemini_429(exc, model_name)
    console.print(f"[yellow]{summary}[/yellow]")  # type: ignore[union-attr]
    if debug:
        console.print(f"  [dim][debug] {exc}[/dim]")  # type: ignore[union-attr]
    return summary, is_daily, retry_wait
