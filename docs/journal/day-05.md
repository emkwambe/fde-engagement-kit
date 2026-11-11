# Learning Journal - Day 5 (2026-11-11)

> Draft written by Claude from the session record. Rewrite each explanation in your own words before you treat it as final - that rewrite is the learning step.

## Skills worked on
S-22 (discovery), S-23 (documentation), S-24 (delivery), S-03/S-04 (config-driven ETL and schemas), S-13 (evals) (see [skills matrix](../03-skills-matrix.md))

## What I built / ran
- A refactor that made the kit generic, then a second customer in a different industry with no core change.
- One more real-eval step: the case that once failed (q-018) now passes with the real model.

## Explain it in 5 sentences (as if to an interviewer)

**Making a kit generic**
1. I listed every place where `core/` knew the first customer: table names, the data generator, the prompt, the fake model's script, a tool name in scoring, the refusal text, the console examples.
2. Each became either a config field (when it is data) or an engagement-owned file (when it is code, like a data generator).
3. I moved the first customer's prompt out without changing a byte, and proved it with a hash, so earlier eval results stayed valid.
4. I tagged the commit, built the second customer, and showed `git diff kit-generic..HEAD -- core/` is empty.
5. One gap only appeared while planning the second customer (two foreign keys, one optional), and I fixed it before the tag.

**Onboarding a customer**
1. Discovery first: the problem in the customer's words, the systems, and which actions need approval.
2. Then documents, then the customer's tables in their own schema, then the config that maps them.
3. The mock system enforces the customer's business rules, so the agent's mistakes surface as errors.
4. Golden facts are computed from the data, never typed by hand.
5. The fake eval proves the wiring; only the real eval measures quality, and that waits for quota.

## What confused me, and how I resolved it
- Which commit did CI build on a pull request? GitHub tests a merge commit, not the branch head; I had named the wrong one in two notes and corrected it.

## One thing I'd do differently
- List the kit gaps by reading the second customer's discovery doc before refactoring; it would have found the foreign-key gap earlier.

## Open questions -> backlog
- Should engagement-owned Python (seed, fake scripts) be sandboxed or reviewed differently from core code?

## Confidence today (1-5) per skill
| Skill | Level |
|---|---|
| S-22 Discovery | (the author rates this) |
| S-24 Delivery management | (the author rates this) |
