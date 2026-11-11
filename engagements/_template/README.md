# Engagement template

```
_template/
├── engagement.yaml      # all customer-specific configuration
├── discovery.md         # copy of playbook/01-discovery-template.md, filled in
├── data/
│   ├── docs/            # sample or exported documents
│   └── tables/          # CSV/JSON exports
├── specs/               # OpenAPI specs of customer systems
├── evals/
│   ├── golden.jsonl     # written WITH the customer
│   └── reports/         # generated eval reports
└── extensions/          # custom tools — last resort (see ADR-004)
```

Steps: see [playbook/README.md](../../playbook/README.md#starting-a-new-engagement).
