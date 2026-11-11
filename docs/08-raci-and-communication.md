# RACI & Communication Plan

This is a solo project, but the roles are separated on purpose to practice how a real FDE engagement works. Wearing a specific "hat" for each decision makes the reasoning visible.

## 1. Roles (hats)

| Role | Played by | Responsibility |
|---|---|---|
| Sponsor | E. Mkwambe | Approves charter, scope changes, closure |
| Project manager | E. Mkwambe | Schedule, risks, status, change control |
| FDE / lead engineer | E. Mkwambe | Design, build, deploy |
| Customer champion (simulated) | E. Mkwambe as "Northwind ops lead" | Describes the problem, writes golden set with FDE, accepts pilot |
| Peer reviewer | 1–2 trusted peers (optional) | Review README + demo video before publishing |

## 2. RACI

R = Responsible, A = Accountable, C = Consulted, I = Informed

| Activity | Sponsor | PM | FDE | Customer champion | Peer reviewer |
|---|---|---|---|---|---|
| Charter & scope | A | R | C | C | – |
| Discovery & problem statement | I | C | R | A | – |
| Architecture & ADRs | I | C | A/R | C | C |
| Build core & engagements | I | I | A/R | C | – |
| Golden set & acceptance thresholds | I | C | R | A | – |
| Security controls | A | C | R | C | – |
| Deployment | I | C | A/R | I | – |
| Demo & handoff | A | R | R | C | C |
| Closure & lessons learned | A | R | C | C | I |

## 3. Communication plan

| Communication | Audience | Frequency | Format | Location |
|---|---|---|---|---|
| Daily journal | Self (learning) | Every session | Markdown | `docs/journal/day-NN.md` |
| Daily status | Sponsor (self), future reviewers | Every session | Status template | `docs/status/day-NN.md` |
| Decision records | Reviewers, future self | As decided | ADR | `docs/adr/` |
| Change requests | Sponsor | As needed | Log entry | `docs/14-decision-and-change-log.md` |
| Demo | Hiring managers, peers | Day 5 | ≤ 5-min video | README link |
| Closure report | Sponsor, reviewers | Day 5 | Report | `docs/15-closure-report.md` |
| Public update (optional) | Network / recruiters | After Day 5 | LinkedIn post + repo link | — |

## 4. Escalation
If a milestone is missed by more than half a session: PM applies cut lines from the WBS, logs the change, and informs the sponsor in the next status report.
