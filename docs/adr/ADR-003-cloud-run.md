# ADR-003: Deploy to GCP Cloud Run (Kubernetes on kind for k8s skills)

- **Status:** Accepted
- **Date:** 2026-11-09
- **Related:** D-13, D-15, S-17, S-19, S-20

## Context
We need a real cloud deployment within one sprint and a small budget, and we also need demonstrable Kubernetes skills.

## Options
1. **Cloud Run** — container to HTTPS URL quickly, scales to zero, simple Terraform.
2. **GKE** — real Kubernetes in the cloud, but cluster cost and setup time.
3. **AWS ECS/App Runner or Azure Container Apps** — equivalent, but more networking/IAM setup for a first deployment.

## Decision
Cloud Run for the cloud deployment. Kubernetes skills shown with a Helm chart running on kind locally and in CI. The same image runs in Compose, kind, and Cloud Run (NFR-11).

## Consequences
- ✅ Low cost (scale to zero), fast to provision.
- ✅ Helm chart is portable to GKE/EKS/AKS later.
- ⚠️ No managed Kubernetes in the cloud this sprint — stated openly in README.
- ⚠️ Cloud SQL does not scale to zero; stop or destroy it after the demo.
