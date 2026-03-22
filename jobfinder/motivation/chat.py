"""Motivation chat — multi-turn LLM conversation to understand user's job search preferences.

The LLM asks 1-2 clarifying questions, then produces a structured summary
that augments resume context during company discovery.
"""

from __future__ import annotations

import json
import os
import re

from jobfinder.config import AppConfig

_MAX_TURNS = 6  # force summary after this many user messages

SYSTEM_PROMPT = """\
You are a career counselor helping someone refine their job search preferences. \
Your goal is to understand what kind of companies they want to work for so we \
can find the best matches.

Based on their input (and their resume if provided), understand:
1. What industries or domains interest them
2. What company characteristics matter (stage, size, culture, location, pace)
3. The relative importance of each factor they mention

Rules:
- Ask only 1 focused follow-up question to clarify or narrow down their preferences.
- If they are too vague, ask them to be more specific.
- If they are too narrow, gently suggest broadening.
- If their input is irrelevant to a job search, steer them back to describing \
the kind of companies they want to work for.
- Once you have enough clarity (typically after 1-2 exchanges), set ready=true \
and provide a concise summary.
- After {max_turns} user messages, you MUST set ready=true and summarize what \
you have so far.

You MUST respond with ONLY a JSON object in this exact format (no markdown, no \
extra text):
{{"reply": "your conversational message", "ready": false}}
or when done:
{{"reply": "your final message confirming preferences", "ready": true, \
"summary": "concise 2-3 sentence summary of their ideal company profile"}}
""".replace("{max_turns}", str(_MAX_TURNS))


def _build_system_prompt(resume_summary: str | None) -> str:
    prompt = SYSTEM_PROMPT
    if resume_summary:
        prompt += (
            f"\n\nThe user's resume summary for context (use this to give more "
            f"relevant suggestions, but focus on their stated preferences):\n"
            f"{resume_summary}"
        )
    return prompt


def _build_messages(chat_history: list[dict]) -> list[dict]:
    """Convert chat_history [{role, content}] to LLM message format."""
    return [{"role": m["role"], "content": m["content"]} for m in chat_history]


def _parse_llm_response(raw: str) -> dict:
    """Parse the LLM's JSON response, handling markdown code fences."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?\s*```$", "", cleaned)

    # Try to find JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        # Fallback: treat the whole response as a reply
        return {"reply": raw.strip(), "ready": False}

    try:
        result = json.loads(cleaned[start : end + 1])
        if "reply" not in result:
            result["reply"] = raw.strip()
        if "ready" not in result:
            result["ready"] = False
        return result
    except json.JSONDecodeError:
        return {"reply": raw.strip(), "ready": False}


def motivation_chat_turn(
    chat_history: list[dict],
    config: AppConfig,
    *,
    resume_summary: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Process one turn of the motivation chat.

    Args:
        chat_history: Full conversation so far including the latest user message.
        config: App config with model_provider and model settings.
        resume_summary: Optional resume text for context.
        api_key: Resolved API key.

    Returns:
        dict with keys: reply (str), ready (bool), summary (str | None)
    """
    from jobfinder.utils.log_stream import log

    system = _build_system_prompt(resume_summary)
    messages = _build_messages(chat_history)

    # Count user messages — force summary if over limit
    user_turns = sum(1 for m in chat_history if m["role"] == "user")
    if user_turns >= _MAX_TURNS:
        system += "\n\nIMPORTANT: This is the user's final message. You MUST set ready=true and provide a summary now."

    log("[dim]Motivation chat: calling LLM...[/dim]")

    if config.model_provider == "gemini":
        raw = _call_gemini(system, messages, config, api_key=api_key)
    else:
        raw = _call_anthropic(system, messages, config, api_key=api_key)

    result = _parse_llm_response(raw)
    log(f"[dim]Motivation chat: ready={result.get('ready', False)}[/dim]")

    return {
        "reply": result["reply"],
        "ready": bool(result.get("ready", False)),
        "summary": result.get("summary"),
    }


def generate_summary(
    chat_history: list[dict],
    config: AppConfig,
    *,
    resume_summary: str | None = None,
    api_key: str | None = None,
) -> str:
    """Force-generate a summary from an existing conversation."""
    system = _build_system_prompt(resume_summary)
    system += (
        "\n\nIMPORTANT: Summarize the user's preferences into a concise 2-3 "
        "sentence company profile. Respond with ONLY a JSON object: "
        '{"reply": "...", "ready": true, "summary": "..."}'
    )
    messages = _build_messages(chat_history)

    if config.model_provider == "gemini":
        raw = _call_gemini(system, messages, config, api_key=api_key)
    else:
        raw = _call_anthropic(system, messages, config, api_key=api_key)

    result = _parse_llm_response(raw)
    return result.get("summary") or result.get("reply", "")


def _call_anthropic(
    system: str,
    messages: list[dict],
    config: AppConfig,
    *,
    api_key: str | None = None,
) -> str:
    from jobfinder.utils.throttle import get_limiter
    get_limiter(config.rpm_limit).wait()

    import anthropic

    client = anthropic.Anthropic(**({"api_key": api_key} if api_key else {}))
    response = client.messages.create(
        model=config.anthropic_model,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def _call_gemini(
    system: str,
    messages: list[dict],
    config: AppConfig,
    *,
    api_key: str | None = None,
) -> str:
    from jobfinder.utils.throttle import get_limiter
    get_limiter(config.rpm_limit).wait()

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))

    # Convert messages to Gemini format
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))

    response = client.models.generate_content(
        model=config.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
        ),
    )
    return response.text or ""
