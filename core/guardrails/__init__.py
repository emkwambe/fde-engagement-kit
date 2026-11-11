"""Guardrails (Day 3, part 1, NFR-07, T-01/T-02/T-04): deterministic checks around the LLM.

  pii.redact(text, kinds)          emails / phones / SSNs -> [EMAIL] / [PHONE] / [SSN]
  injection.find_injection(text)   phrases that try to give the AI instructions
  injection.neutralize(text)       replaces those lines with a visible marker
  tools.guard_tools(tools, cfg)    applies both to every tool result before the model sees it
  input.check_input(text, cfg)     blocks direct injection attempts in user messages

They are plain regexes on purpose: fast, free, testable, and they work with ANY model. They are one
layer of several (system prompt rules, read-only SQL, human approval for writes), never the only one.
"""

from core.guardrails.injection import find_injection, neutralize
from core.guardrails.input import BLOCKED_ANSWER, check_input
from core.guardrails.pii import redact

__all__ = ["BLOCKED_ANSWER", "check_input", "find_injection", "neutralize", "redact"]
