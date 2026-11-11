# Learning Journal - Day 4 (2026-11-11)

> Draft written by Claude from the session record and the CI logs. Rewrite each explanation in your own words before you treat it as final - that rewrite is the learning step.

## Skills worked on
S-16 (containers), S-17 (Kubernetes/Helm), S-18 (CI/CD), S-19 (Terraform), S-20 (cloud deployment) (see [skills matrix](../03-skills-matrix.md))

## What I built / ran
- Two container images, a Compose stack with one-shot jobs, a Helm chart, three GitHub Actions workflows, and Terraform for Cloud Run.
- Everything heavy ran in CI, because the laptop was short of memory. The CI run is the clean-machine proof.

## Explain it in 5 sentences (as if to an interviewer)

**Containers and CI**
1. The images are multi-stage: uv builds the virtual environment in one stage, and the runtime stage gets only the environment and the code.
2. Base images are pinned by digest for repeatable builds, and the runtime stage installs OS security updates, because a frozen base also freezes old vulnerabilities.
3. CI builds the images on every push, refuses any CRITICAL vulnerability that has a fix, and then starts the whole stack twice: with Compose and on a kind cluster.
4. The commit is baked into the image and shown by /health, and CI checks that the running stack reports the commit it built.
5. The real-model eval and the cloud deploy are manual workflows: one costs money and quota, the other needs the owner's approval and uses keyless federation.

**Kubernetes and Terraform**
1. Helm turns the deployment into a form with defaults, so a new customer changes values, not templates.
2. Init containers seed and migrate before the API starts, so the API never serves an empty database.
3. Terraform describes Cloud SQL, Cloud Run, secrets and identities; plan shows the change, apply makes it, destroy removes it.
4. Terraform owns the infrastructure and ignores image changes, so the deploy pipeline can roll out new images without a fight.
5. The stack costs about four cents an hour, almost all of it the database, so destroy is part of the runbook, not an afterthought.

## What confused me, and how I resolved it
- The first CI run failed on trivy although the base image was pinned. Pinning freezes vulnerabilities too; the fix is upgrading OS packages at build time.
- `docker compose up --wait` and one-shot jobs: wait for the API service, and let the jobs' exit code 0 count as success through `service_completed_successfully`.

## One thing I'd do differently
- Check free memory before planning local container work; plan CI-first when the laptop is tight.

## Open questions -> backlog
- Should /health return 503 when degraded, so Kubernetes stops routing to a pod with a broken database? (Trade-off: a database outage would then restart every pod.)

## Confidence today (1-5) per skill
| Skill | Level |
|---|---|
| S-16 Containers | (the author rates this) |
| S-17 Kubernetes | (the author rates this) |
| S-18 CI/CD | (the author rates this) |
| S-19 Terraform | (the author rates this) |
