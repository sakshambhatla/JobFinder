"""LLM-powered offer evaluation for pipeline entries in the offer stage.

Analyzes a company across 10 dimensions, producing scored assessments
with red/yellow/green flags and a weighted overall score.
"""

from __future__ import annotations

import json
import logging
import re

log = logging.getLogger(__name__)


# ── Prompt ──────────────────────────────────────────────────────────────────


def _build_offer_prompt(
    company_name: str,
    role_title: str | None,
    personal_context: str,
) -> str:
    role_desc = f" for a {role_title} position" if role_title else ""
    context_block = (
        f"\n\nContext about my situation:\n{personal_context}"
        if personal_context.strip()
        else ""
    )

    return f"""You are helping me evaluate a job offer from {company_name}{role_desc}. I want a structured, honest assessment that helps me decide whether to accept.

First, gather what you can from public sources: Glassdoor, Blind, LinkedIn, Crunchbase, news coverage, and any engineering blogs or talks from the company. Note the recency and volume of each signal.

Then evaluate the company across these 10 dimensions. For each, give a score from 1-5, a 2-3 sentence rationale grounded in evidence, and a red/yellow/green flag.

1. Business trajectory (weight: 1.5x) — Is the company growing, stagnant, or declining? Look at funding history, revenue signals, headcount trends, recent layoffs, and market position.
2. Financial stability & runway (weight: 1.5x) — How safe is my job in the next 12-24 months? For startups: last funding round, burn rate estimates. For public/mature companies: revenue trend, debt, market cap stability.
3. Management quality (weight: 1.5x) — Do leaders know what they're doing and treat people well? Look at Glassdoor sentiment on management, CEO approval rating, Blind reviews, leadership team LinkedIn tenure.
4. Engineering culture & talent density (weight: 1.5x) — Would I be surrounded by people I can learn from? Look for engineering blogs, conference talks, open source contributions, recent hire backgrounds.
5. Work-life balance & pace (weight: 1.0x) — Is this a place I can sustain for 2+ years? Look at WLB Glassdoor ratings, on-call burden, crunch culture, remote/flexible work.
6. Compensation & equity (weight: 1.0x) — Is the total package competitive and is the equity real? Consider base, bonus, equity grant size/vesting, 409A vs preferred price for startups.
7. Career growth & scope (weight: 1.0x) — Will this role accelerate my career or stall it? Look at internal promotions, role budget/headcount authority, brand recognition for future roles.
8. Mission & product clarity (weight: 1.0x) — Is the company building something real with staying power? Evaluate value proposition, customer traction, defensibility.
9. Org health & stability (weight: 1.0x) — Is the internal structure functional? Look for reorgs, manager turnover, siloed/political teams, senior engineers leaving after <1 year.
10. Location & logistics fit (weight: 1.0x) — Does the physical setup work? Consider commute, in-office days, timezone for remote, cost of living adjustment.

After scoring all 10 dimensions, compute:
- weighted_score: (sum of score*weight) / (sum of weights), where dimensions 1-4 have weight 1.5 and dimensions 5-10 have weight 1.0. Round to 1 decimal.
- raw_average: simple average of all 10 scores. Round to 1 decimal.
- verdict: 3 sentences — what this company is, what the key risk is, and whether you'd recommend accepting.
- key_question: The single most important question I should ask in my final negotiation or due diligence call.

Return ONLY a JSON object (no markdown fences, no commentary) with this exact structure:
{{
  "dimensions": [
    {{"name": "Business trajectory", "score": 4, "weight": 1.5, "rationale": "...", "flag": "green"}},
    ...
  ],
  "weighted_score": 3.8,
  "raw_average": 3.5,
  "verdict": "...",
  "key_question": "...",
  "flags": {{"red": 1, "yellow": 3, "green": 6}}
}}{context_block}"""


# ── LLM Calls (reuse from reasoning.py) ────────────────────────────────────


def _call_anthropic(prompt: str, api_key: str, model: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _call_gemini(prompt: str, api_key: str, model: str) -> str:
    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text


# ── Response Parser ─────────────────────────────────────────────────────────


def _parse_offer_response(text: str) -> dict:
    """Parse LLM JSON response into a validated offer analysis dict."""
    # Strip markdown fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        log.error("Failed to parse offer analysis JSON: %s", text[:200])
        return {
            "dimensions": [],
            "weighted_score": None,
            "raw_average": None,
            "verdict": "Analysis failed — could not parse LLM response.",
            "key_question": None,
            "flags": {"red": 0, "yellow": 0, "green": 0},
        }

    # Validate and normalize dimensions
    dimensions = []
    for dim in data.get("dimensions", []):
        score = dim.get("score", 3)
        if not isinstance(score, (int, float)) or score < 1:
            score = 1
        elif score > 5:
            score = 5
        score = int(score)

        flag = dim.get("flag", "yellow")
        if flag not in ("red", "yellow", "green"):
            flag = "green" if score >= 4 else "yellow" if score >= 3 else "red"

        dimensions.append({
            "name": dim.get("name", "Unknown"),
            "score": score,
            "weight": float(dim.get("weight", 1.0)),
            "rationale": dim.get("rationale", ""),
            "flag": flag,
        })

    # Recompute flag counts from actual dimensions
    flags = {"red": 0, "yellow": 0, "green": 0}
    for d in dimensions:
        flags[d["flag"]] = flags.get(d["flag"], 0) + 1

    # Recompute scores from dimensions for accuracy
    if dimensions:
        total_weighted = sum(d["score"] * d["weight"] for d in dimensions)
        total_weight = sum(d["weight"] for d in dimensions)
        weighted_score = round(total_weighted / total_weight, 1) if total_weight else None
        raw_average = round(sum(d["score"] for d in dimensions) / len(dimensions), 1)
    else:
        weighted_score = data.get("weighted_score")
        raw_average = data.get("raw_average")

    return {
        "dimensions": dimensions,
        "weighted_score": weighted_score,
        "raw_average": raw_average,
        "verdict": data.get("verdict"),
        "key_question": data.get("key_question"),
        "flags": flags,
    }


# ── Public API ──────────────────────────────────────────────────────────────


def analyze_offer(
    company_name: str,
    role_title: str | None,
    personal_context: str,
    api_key: str,
    model_provider: str = "anthropic",
    model_name: str | None = None,
) -> dict:
    """Run LLM offer analysis and return parsed result dict."""
    prompt = _build_offer_prompt(company_name, role_title, personal_context)

    if model_provider == "anthropic":
        text = _call_anthropic(prompt, api_key, model_name or "claude-sonnet-4-6")
    elif model_provider == "gemini":
        text = _call_gemini(prompt, api_key, model_name or "gemini-2.5-flash-lite")
    else:
        raise ValueError(f"Unsupported model provider: {model_provider}")

    return _parse_offer_response(text)
