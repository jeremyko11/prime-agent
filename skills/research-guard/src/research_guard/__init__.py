"""Research guardrails: trimming, budget caps, append-only logs."""
from ._impl import run, trim, log_event, budget, consume, check, status

__all__ = ["run", "trim", "log_event", "budget", "consume", "check", "status"]
