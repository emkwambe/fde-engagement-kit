# ADR-001: Use LangGraph for the agent

- **Status:** Accepted
- **Date:** 2026-11-09
- **Related:** FR-09, FR-10, S-10

## Context
The agent must call several tools, pause before write operations for human approval, resume later (possibly after a restart), and be inspectable step by step. The job description lists LangChain and LangGraph as preferred skills.

## Options
1. **LangGraph** — explicit state graph, checkpointers, built-in interrupts for human-in-the-loop.
2. **Plain LangChain agent / custom while-loop** — simple, but approval/resume and persistence must be hand-built.
3. **LlamaIndex workflows** — strong for RAG, less common in the target job postings for agent orchestration.

## Decision
Use LangGraph with a Postgres checkpointer. Keep tools as plain LangChain tools so they're reusable outside the graph.

## Consequences
- ✅ Approvals, persistence, and step-level tracing come mostly for free.
- ✅ Graph is easy to draw and explain in an interview.
- ⚠️ Framework APIs change often; pin versions and keep graph code thin.
- ⚠️ Learning curve on Day 2 — budgeted as 📖 time.
