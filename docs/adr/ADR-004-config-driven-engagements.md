# ADR-004: Customer specifics live in config-driven engagement folders

- **Status:** Accepted
- **Date:** 2026-11-09
- **Related:** NFR-02, SC-02

## Context
The project must be reusable for real, similar situations. FDEs repeatedly face the same pattern — documents + database + API + workflow — with different details.

## Options
1. **Fork the repo per customer** — fast at first, drifts quickly, fixes don't propagate.
2. **Customer plugin code** — flexible, but every customer means new code.
3. **Config-driven engagements with an escape hatch** — YAML declares sources, tools, models, evals, deploy target; optional `engagements/<name>/extensions/` for genuinely custom tools.

## Decision
Option 3. The core reads `engagement.yaml`; tools come from OpenAPI specs and SQL introspection. Custom Python tools are allowed only in the engagement's `extensions/` folder and are registered by config.

## Consequences
- ✅ New engagement = discovery + config + golden set; proven by engagement #2 with zero core diff.
- ✅ Core improvements benefit all engagements.
- ⚠️ Risk of over-generalizing in a 1-week sprint — only generalize what engagement #1 or #2 actually needs.
