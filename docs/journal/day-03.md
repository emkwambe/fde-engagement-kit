# Learning Journal - Day 3 (2026-11-11)

> Draft written by Claude from the session record and the eval reports. Rewrite each explanation in your own words before you treat it as final - that rewrite is the learning step.

## Skills worked on
S-13 (evaluation), S-14 (AI security / guardrails), S-08 (LLM APIs) (see [skills matrix](../03-skills-matrix.md))

## What I built / ran
- Guardrails: deterministic regex layers for PII and prompt injection around every tool result and RAG chunk; direct attacks refused before the model is called.
- A 27-case golden set and a runner that scores six checks per case and writes a report I can commit and compare.
- Three real-model runs. Each one failed in a new way, and each failure became a fix with a test.

## Explain it in 5 sentences (as if to an interviewer)

**Evals**
1. Each golden case says what a correct run must show: which tools, which sources, which facts, whether it must pause for approval, and what must never appear.
2. A case passes only if every check that applies passes, and the gate needs 85% overall and 100% on the red-team cases.
3. The fake model proves the harness works for free; only the real model's score can pass or fail the gate.
4. When the provider's daily quota runs out, the remaining cases are "not run", not failed, and the run is resumed later from its JSON report.
5. Resumed results must come from the same model and prompt, and their cost belongs to the run that produced them.

**What the real runs taught**
1. A model can reject a parameter the library sends by default, so configuration should only send what you set.
2. Newer models return content as a list of blocks; reading `.text` instead of `str(content)` is the safe way to get the answer.
3. A failing eval case can be the clue to a product bug: q-018's "wrong wording" was a raw list shown to users.
4. A string-match check can be too strict; widening it is fine only with evidence that the answer was right.
5. Numbers in a report must say what this run did, or they mislead the reader who uses them for cost planning.

## What confused me, and how I resolved it
- Why did the first run "pass" 2 cases with zero tokens? Those red-team cases are refused by the input guardrail before any model call.
- Why did the resumed run show a cost although nothing ran? The runner added up the reused results; fixed in Sprint 01.

## One thing I'd do differently
- Do a one-case real smoke run before a full run: it would have caught the temperature error for one request instead of 27.

## Open questions -> backlog
- Should the eval also report a per-category cost, to see which kinds of questions are expensive?
- Is an LLM-as-judge worth adding as a secondary check for answers that are right but worded differently?

## Confidence today (1-5) per skill
| Skill | Level |
|---|---|
| S-13 Evaluation | (author to fill) |
| S-14 Guardrails | (author to fill) |
