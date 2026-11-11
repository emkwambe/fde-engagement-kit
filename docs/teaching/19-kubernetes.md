# 19 - Running on Kubernetes

Component: `deploy/helm/fde-kit/` (`Chart.yaml`, `values.yaml`, `templates/`), `.\tasks.ps1 images | kind-up | kind-down`, CI job `containers` (steps "Helm install on kind", "/health through port-forward")

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| A Helm chart that installs the API (with seed and migrate init containers), the mock ERP, and Postgres + pgvector for kind only; engagement config as a ConfigMap, tokens as a Secret, `/health` probes | Local Kubernetes on kind, and every CI run; the same chart pattern applies to GKE/EKS/AKS with Postgres switched off | Templates fill in names, images and settings from `values.yaml`; init containers prepare data before the API starts; non-root, read-only root filesystem, all capabilities dropped | Many customers run Kubernetes. A chart turns "how to run it" into versioned, reviewable config, and probes let the cluster restart or hold traffic from an unhealthy pod |

## ELI10

Kubernetes is a building manager for containers. You hand over a list ("one API, one ERP, one database; this is what
healthy looks like") and the manager keeps it true: if a container crashes, a new one is started; if one stops answering
its health check, it is restarted; nobody is sent to a room that is not ready yet.

Helm is the form you fill in for the manager. The chart is a blank form with sensible defaults (`values.yaml`); for a
new customer you change a few boxes (`--set engagement=...`, `--set-file engagementConfig=...`) instead of rewriting the
whole list. That is the kit's promise again: config, not code.

Where the analogy stops: the manager only knows what you told it. A pod whose `/health` answers 200 while its database
is broken still counts as healthy: our `/health` says `degraded` inside the body, but the probe only reads the status code.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Is the chart valid, and what will it create?"

> [!IMPORTANT]
> **CONTEXT - When / where?** On the author's laptop, no cluster needed: `helm lint` checks the chart, `helm template` renders the manifests without installing anything.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> helm lint deploy/helm/fde-kit --set-file engagementConfig=engagements/demo-logistics/engagement.yaml
> helm template fde deploy/helm/fde-kit --set-file engagementConfig=engagements/demo-logistics/engagement.yaml | Select-String '^kind:|^  name:' | ForEach-Object Line
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> ==> Linting deploy/helm/fde-kit
> [INFO] Chart.yaml: icon is recommended
>
> 1 chart(s) linted, 0 chart(s) failed
>
> kind: Secret          name: fde-secrets
> kind: ConfigMap       name: fde-engagement
> kind: Service         name: fde-api
> kind: Service         name: fde-mock-erp
> kind: Service         name: fde-postgres
> kind: Deployment      name: fde-api
> kind: Deployment      name: fde-mock-erp
> kind: StatefulSet     name: fde-postgres
> (shown side by side here; the command prints them on alternating lines)
> 8 objects. Postgres is a StatefulSet (stable name + its own disk), the others are Deployments.
> The ConfigMap only exists because engagementConfig was passed: config changes without a new image.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "Does it actually run on a cluster: every pod Ready and /health ok?"

> [!IMPORTANT]
> **CONTEXT - When / where?** CI run 43035141379, job `containers`: kind cluster `fde` created by `helm/kind-action`, both images loaded with `kind load docker-image`, then `helm upgrade --install ... --wait`. Run in CI because the laptop was under its 3 GB free-memory floor (risk R-10's own mitigation). Locally: runbook section 3.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> gh run view --job 130572443115 --log | Select-String 'STATUS: deployed|fde-(api|mock-erp|postgres)-\S+\s+1/1|kind health ok' | ForEach-Object { ($_.Line -split "`t")[-1] -replace '^\S+Z ', '' }
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> STATUS: deployed
> fde-api-5854dd66fd-k4hqt        1/1     Running   0          26s   10.244.0.6   fde-control-plane ...
> fde-mock-erp-6fb66c958d-l22qt   1/1     Running   0          26s   10.244.0.5   fde-control-plane ...
> fde-postgres-0                  1/1     Running   0          26s   10.244.0.8   fde-control-plane ...
> kind health ok {'app': '0.3.0', 'build_sha': '37a85e0'}
> All three pods Ready 26 s after install. The API pod only started after its init containers finished: "seed"
> wrote the CSVs, "migrate" waited for Postgres, applied migrations, created the read-only role and loaded the
> data. /health through `kubectl port-forward` reports status ok and the same commit as the Compose test.
> ```

## Teach-back check

<details><summary>1. Why init containers instead of doing migrations when the API starts?</summary>

Kubernetes runs init containers in order and starts the main container only after all of them succeed, so the API never serves an empty database. They also keep the API's start fast and simple, and a failed migration is visible as an init error instead of a crash loop.
</details>

<details><summary>2. Why is the chart's Postgres "for kind only"?</summary>

In the cloud the database is managed (Cloud SQL: backups, patching, storage). Running your own database in a cluster is a real operations job. The chart switches it off with postgres.enabled=false and takes the database URL from a Secret instead.
</details>

<details><summary>3. What do readOnlyRootFilesystem and runAsNonRoot protect against?</summary>

If someone gets code execution inside the container, they cannot change the application files or install tools (read-only root, only /tmp is writable), and they are not root, so escaping to the node is much harder. Our images were built for this: fixed uid 10001, HOME=/tmp, no bytecode writes.
</details>

## Interview line

"A Helm chart deploys the agent with init containers for seeding and migrations, the engagement config as a ConfigMap, hardened non-root pods and /health probes, and CI installs it on a kind cluster on every push and checks every pod is Ready."
