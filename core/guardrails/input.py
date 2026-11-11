"""Input guardrail: refuse direct prompt-injection attempts before they reach the model (T-02).

A user message that tries to override the agent's rules ("ignore your rules and ...") is answered with a
fixed refusal. The model is never called, no tool can run, and the attempt is recorded in the audit log.
Ordinary questions pass through untouched.
"""

from __future__ import annotations

from core.config.schema import Guardrails
from core.guardrails.injection import find_injection

# The reply text is configured per engagement (guardrails.blocked_answer); this is the kit's default wording.
BLOCKED_ANSWER = Guardrails.model_fields["blocked_answer"].default


def check_input(message: str, cfg: Guardrails) -> list[str]:
    """Matched injection phrases (empty = allowed). Disabled when guardrails.injection_filter is false."""
    return find_injection(message) if cfg.injection_filter else []
