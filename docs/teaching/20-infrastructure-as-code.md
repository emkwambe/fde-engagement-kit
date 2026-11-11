# 20 - Infrastructure as code

Component: `deploy/terraform/gcp/` (`versions.tf`, `variables.tf`, `main.tf`, `outputs.tf`, `.terraform.lock.hcl`), `docs/11-deployment-runbook.md` sections 4 and 7

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| Terraform that describes the whole GCP deployment: APIs, Artifact Registry, Cloud SQL Postgres 16, Secret Manager, two service accounts, Cloud Run (API, mock ERP, ingest job), Workload Identity Federation for GitHub | Prepared and validated now; applied only by the human (CLAUDE.md rule 5), then destroyed after the demo | Declarative files: you describe the end state, `plan` shows the difference to reality, `apply` makes it so, `destroy` removes it all. State lives in a private GCS bucket | Clicking in a console cannot be reviewed, repeated or undone reliably. Code can: the same files rebuild the stack in any project, and `destroy` guarantees the expensive parts are really gone |

## ELI10

Terraform is a shopping list plus a very careful shop assistant. You write down what you want ("one small database,
two web services, three secrets"). The assistant compares the list with what is already in your cupboard (the state),
tells you exactly what it will buy or throw away (`plan`), and only does it when you say yes (`apply`). When the party
is over, `destroy` returns everything, so you stop paying for it.

Where the analogy stops: the list can be perfect and the shop can still say no. `validate` only checks that the list is
well written. Quotas, organisation policies (for example "no public services") or a missing billing account only show up
at `plan`/`apply` time, which is the human's step.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Is the Terraform well formed and internally consistent, without creating anything?"

> [!IMPORTANT]
> **CONTEXT - When / where?** The author's laptop. `init -backend=false` downloads the providers but does not touch any state bucket; `fmt -check` and `validate` never call GCP. Nothing billable happens.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> terraform -chdir=deploy/terraform/gcp init -backend=false -input=false
> terraform -chdir=deploy/terraform/gcp fmt -check -recursive; "fmt exit code: $LASTEXITCODE"
> terraform -chdir=deploy/terraform/gcp validate
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> ...
> If you ever set or change modules or backend configuration for Terraform,
> rerun this command to reinitialize your working directory. ...
> fmt exit code: 0
> Success! The configuration is valid.
> Providers selected (from the lock file): hashicorp/google 7.46.2, hashicorp/random 3.9.1.
> The lock file is committed, so the human's apply uses exactly these provider versions.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "What will it cost while it exists, and how do I make sure it stops?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Unit prices from `docs/12-cost-estimate.md`: Cloud SQL `db-g1-small` $0.035/h, SSD $0.000232877/GiB-hour, 10 GiB. Cloud Run scales to zero (`min_instance_count = 0`) and stays in the free tier at demo volume.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> $sql = 0.035; $disk = 10 * 0.000232877
> 'per hour {0:N4}  per day {1:N3}  per 30 days {2:N2}' -f ($sql + $disk), (($sql + $disk) * 24), (($sql + $disk) * 730)
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> per hour 0.0373  per day 0.896  per 30 days 27.25
> About 4 cents an hour, almost all of it the database, which runs whether or not anyone uses the demo.
> That is why the runbook ends with `terraform destroy` and a check that `gcloud sql instances list` is empty,
> and why deletion_protection is false on the instance (it would block destroy). For real customer data you
> would turn it back on.
> ```

## Teach-back check

<details><summary>1. Why does Terraform create the OpenAI secret but not its value?</summary>

Everything Terraform sets ends up in its state file. Generated values (database passwords, tokens) have to be there; the OpenAI key does not, so the human adds it as a secret version with gcloud and Terraform never sees it.
</details>

<details><summary>2. Terraform creates the Cloud Run services, but deploy.yml changes their images. Why don't they fight?</summary>

The services have lifecycle ignore_changes on the container image. Terraform owns the infrastructure (scaling, secrets, service account, Cloud SQL connection); the pipeline owns which image runs. Without that, every terraform apply would roll back to the image tag in its variables.
</details>

<details><summary>3. Why is the API NOT public, but the mock ERP is? (Sprint 01b, review finding F-R1)</summary>

The first version gave `allUsers` invoke rights on the API. A reviewer pointed out what that means: anyone on the internet could approve a paused write (the "by" name is typed in) or loop /chat to burn the OpenAI quota. Now the API has no public binding: only members of `api_invokers` (and the deploy account, for its smoke test) can call it, people use `gcloud run services proxy fde-api`, and the app adds reviewer and chat tokens on top (DC-031). The mock ERP stays invokable without IAM, with a documented reason: it plays a third-party system that checks its own 40-character token, and our generated tools send that token in the Authorization header that Cloud Run IAM would also need. Making it IAM-private means sending a Google ID token in X-Serverless-Authorization, a toolgen feature in the backlog.
</details>

<details><summary>4. After `terraform apply`, opening the api_url in a browser gives 403. Is the deploy broken?</summary>

No, that is the point. Cloud Run refuses callers without run.invoker. Run `gcloud run services proxy fde-api --region us-east1 --port 8080` and use http://localhost:8080: the proxy adds your Google identity. Add a colleague to `api_invokers` and apply again to let them in.
</details>

## Interview line

"The GCP deployment is Terraform: Cloud SQL Postgres 16 with pgvector, Secret Manager, least-privilege service accounts, a scale-to-zero Cloud Run API that is reachable only through IAM, and keyless GitHub deploys through Workload Identity Federation; it passes fmt and validate, costs about four cents an hour while it exists, and `destroy` is part of the runbook."
