from __future__ import annotations

from pydantic import BaseModel


class DiscoverCompaniesRequest(BaseModel):
    max_companies: int | None = None
    model_provider: str | None = None  # overrides config
    seed_companies: list[str] | None = None  # if set, use seed-based discovery instead of resume
    resume_id: str | None = None  # UUID of the selected resume (required in resume mode)


class RoleFiltersRequest(BaseModel):
    title: str | None = None
    posted_after: str | None = None
    location: str | None = None
    confidence: str = "high"
    filter_strategy: str | None = None  # "llm" | "fuzzy" | "semantic"; None → use config default


class DiscoverRolesRequest(BaseModel):
    company_names: list[str] | None = None  # limit to specific companies from registry
    company_run_id: str | None = None  # use all companies from a specific company run
    refresh: bool = False
    resume: bool = False  # resume from checkpoint if one exists
    use_cache: bool = False  # re-use cached roles (TTL: 2 days) per company+ATS
    role_filters: RoleFiltersRequest | None = None  # overrides config.role_filters
    relevance_score_criteria: str | None = None  # overrides config
    model_provider: str | None = None  # overrides config
    skip_career_page: bool | None = None  # True → skip Playwright Pass 2; None → use config default


class FetchBrowserRolesRequest(BaseModel):
    company_name: str  # must exist in the company registry
