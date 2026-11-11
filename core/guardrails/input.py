"""Input guardrail: refuse direct prompt-injection attempts before they reach the model (T-02).

A user message that tries to override the agent's rules ("ignore your rules and ...") is answered with a
fixed refusal. The model is never called, no tool can run, and the attempt is recorded in the audit log.
Ordinary questions pass through untouched.
"""

from __future__ import annotations

from core.config.schema import Guardrails
from core.guardrails.injection import find_injection

BLOCKED_ANSWER = ("I can't follow instructions that try to change my rules. I can help with orders, shipments, "
                  "SLA credits and claims within my normal permissions.")


def check_input(message: str, cfg: Guardrails) -> list[str]:
    """Matched injection phrases (empty = allowed). Disabled when guardrails.injection_filter is false."""
    return find_injection(message) if cfg.injection_filter else []
