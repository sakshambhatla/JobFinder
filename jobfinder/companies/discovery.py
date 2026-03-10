from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

from jobfinder.companies.prompts import (
    SEED_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_seed_user_prompt,
    build_user_prompt,
)
from jobfinder.config import AppConfig
from jobfinder.storage.schemas import DiscoveredCompany
from jobfinder.utils.http import head_ok


def discover_companies(
    resumes: list[dict],
    config: AppConfig,
    *,
    seed_companies: list[str] | None = None,
) -> list[DiscoveredCompany]:
    """Discover companies using the configured model provider."""
    if config.model_provider == "gemini":
        raw_text = _call_gemini(resumes, config, seed_companies=seed_companies)
    else:
        raw_text = _call_anthropic(resumes, config, seed_companies=seed_companies)

    companies = _parse_response(raw_text)
    _validate_companies(companies, timeout=config.request_timeout)

    now = datetime.now(timezone.utc).isoformat()
    for c in companies:
        c.discovered_at = now

    return companies


def _call_anthropic(
    resumes: list[dict],
    config: AppConfig,
    *,
    seed_companies: list[str] | None = None,
) -> str:
    from jobfinder.utils.throttle import get_limiter
    get_limiter(config.rpm_limit).wait()

    import anthropic

    client = anthropic.Anthropic()
    if seed_companies:
        system = SEED_SYSTEM_PROMPT
        user_prompt = build_seed_user_prompt(seed_companies, config.max_companies)
    else:
        system = SYSTEM_PROMPT
        user_prompt = build_user_prompt(resumes, config.max_companies)

    print()  # blank line before stream
    chunks: list[str] = []
    with client.messages.stream(
        model=config.anthropic_model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            chunks.append(text)
    print("\n")  # blank line after stream
    return "".join(chunks)


def _call_gemini(
    resumes: list[dict],
    config: AppConfig,
    *,
    seed_companies: list[str] | None = None,
    _attempt: int = 0,
) -> str:
    import time

    from jobfinder.utils.throttle import get_limiter
    get_limiter(config.rpm_limit).wait()

    from google import genai
    from google.genai import types
    from google.genai.errors import ClientError

    from jobfinder.utils.display import console

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    if seed_companies:
        system = SEED_SYSTEM_PROMPT
        user_prompt = build_seed_user_prompt(seed_companies, config.max_companies)
    else:
        system = SYSTEM_PROMPT
        user_prompt = build_user_prompt(resumes, config.max_companies)

    print()  # blank line before stream
    chunks: list[str] = []
    try:
        for chunk in client.models.generate_content_stream(
            model=config.gemini_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        ):
            if chunk.text:
                print(chunk.text, end="", flush=True)
                chunks.append(chunk.text)
    except ClientError as exc:
        if getattr(exc, "code", None) == 429:
            from jobfinder.utils.gemini_errors import log_gemini_429

            summary, is_daily, retry_wait = log_gemini_429(
                exc, config.gemini_model, config.debug, console
            )
            if not is_daily and _attempt < 3:
                console.print(
                    f"[yellow]  Retrying in {retry_wait}s ({_attempt + 1}/3)...[/yellow]"
                )
                time.sleep(retry_wait)
                return _call_gemini(resumes, config, seed_companies=seed_companies, _attempt=_attempt + 1)

            tip = (
                "Daily quota resets at midnight Pacific. Try gemini_model='gemini-2.0-flash' or model_provider='anthropic'."
                if is_daily
                else "Per-minute retries exhausted. Try model_provider='anthropic'."
            )
            raise RuntimeError(f"{summary}\n{tip}") from exc
        raise
    print("\n")  # blank line after stream
    return "".join(chunks)


_ATS_CHECK_URLS: dict[str, str] = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
    "lever": "https://api.lever.co/v0/postings/{token}",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{token}",
}


def _validate_companies(companies: list[DiscoveredCompany], timeout: int = 10) -> None:
    """Validate career_page_url and ats_board_token in place; log warnings for failures."""
    from jobfinder.utils.display import console

    for c in companies:
        if c.career_page_url:
            if not head_ok(c.career_page_url, timeout=timeout):
                console.print(
                    f"  [yellow]⚠[/yellow] {c.name}: career_page_url unreachable — cleared"
                )
                c.career_page_url = ""

        if c.ats_type in _ATS_CHECK_URLS and c.ats_board_token:
            check_url = _ATS_CHECK_URLS[c.ats_type].format(token=c.ats_board_token)
            if not head_ok(check_url, timeout=timeout):
                console.print(
                    f"  [yellow]⚠[/yellow] {c.name}: ats_board_token "
                    f"'{c.ats_board_token}' not found on {c.ats_type} — cleared"
                )
                c.ats_board_token = None


def _parse_response(raw_text: str) -> list[DiscoveredCompany]:
    """Parse a JSON array of companies from an LLM response."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?\s*```$", "", cleaned)

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(
            f"Could not find JSON array in model response:\n{raw_text[:500]}"
        )

    data = json.loads(cleaned[start : end + 1])
    return [DiscoveredCompany.model_validate(item) for item in data]
