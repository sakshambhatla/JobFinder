"""Browser agent session state — streaming, kill signals, metrics, rate-limit strategy."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class AgentMetrics:
    """Live metrics updated throughout a browser agent run."""

    company_name: str
    started_at: float = field(default_factory=time.time)
    steps_taken: int = 0
    jobs_collected: int = 0
    jobs_announced: int | None = None  # total shown on career page, if detectable
    rate_limit_hits: int = 0
    errors: list[str] = field(default_factory=list)
    status: str = "running"  # running | done | rate_limited | killed | error

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.started_at

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "started_at": self.started_at,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "steps_taken": self.steps_taken,
            "jobs_collected": self.jobs_collected,
            "jobs_announced": self.jobs_announced,
            "rate_limit_hits": self.rate_limit_hits,
            "errors": self.errors,
            "status": self.status,
        }


@dataclass
class AgentSession:
    """Per-company session carrying SSE queue, kill signal, and accumulated results."""

    company_name: str
    event_queue: asyncio.Queue  # SSE events drained by the SSE generator
    kill_event: asyncio.Event  # call .set() to stop the agent
    metrics: AgentMetrics
    task: asyncio.Task | None = None  # background asyncio task reference
    partial_roles: list = field(default_factory=list)  # accumulated DiscoveredRole dicts


class RateLimitStrategy:
    """Exponential back-off tracker for career-page API rate limits.

    Usage::

        strategy = RateLimitStrategy(initial_wait=5, max_retries=5)
        wait = strategy.on_rate_limit()
        if wait is None:
            # give up — too many consecutive failures
        else:
            await asyncio.sleep(wait)
        ...
        strategy.on_success()   # reset counters after a successful call
    """

    def __init__(self, initial_wait: int = 5, max_retries: int = 5) -> None:
        self._initial = initial_wait
        self._max_retries = max_retries
        self._current_wait = initial_wait
        self.consecutive_hits: int = 0

    def on_rate_limit(self) -> int | None:
        """Return seconds to wait, or None if max retries exceeded (give up)."""
        self.consecutive_hits += 1
        if self.consecutive_hits > self._max_retries:
            return None
        wait = self._current_wait
        self._current_wait = min(self._current_wait * 2, 120)  # cap at 2 min
        return wait

    def on_success(self) -> None:
        """Reset back-off state after a successful API call."""
        self.consecutive_hits = 0
        self._current_wait = self._initial
