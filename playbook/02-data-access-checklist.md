# Data Access & Security Checklist — <Customer name>

Complete before connecting to any real customer system.

## Documents
- [ ] Source location agreed (bucket / SharePoint export / file share)
- [ ] Read-only access granted to a service identity (not a personal account)
- [ ] Sensitive documents excluded or labeled
- [ ] Refresh frequency agreed (one-time / daily / on change)

## Databases
- [ ] Read-only DB role created (`SELECT` on agreed tables/views only)
- [ ] Views created to hide unneeded or sensitive columns
- [ ] Statement timeout and row limit set
- [ ] Network path agreed (private IP / proxy / allowlist)

## APIs
- [ ] OpenAPI spec obtained (or written from docs)
- [ ] Sandbox / test environment available
- [ ] Credentials scoped to required operations only
- [ ] Write operations listed in `require_approval`
- [ ] Rate limits known

## LLM & data handling
- [ ] Approved LLM provider and region
- [ ] Data retention terms of the provider reviewed by customer
- [ ] PII redaction patterns agreed
- [ ] Logging policy agreed (are prompts/answers stored? how long?)

## Infrastructure
- [ ] Target cloud / project / subscription identified
- [ ] Deployment identity with least privilege
- [ ] Secrets stored in the customer's secret manager
- [ ] Budget / cost alerts configured

## Sign-off
| Name | Role | Date |
|---|---|---|
