# Deployment & Operations Runbook

Parent: [Architecture §5](05-architecture.md#5-deployment-views)

> Validate this runbook by following it literally on Day 4 and Day 5. Fix any step that doesn't work exactly as written.

## 1. Prerequisites (Windows, PowerShell 7)
All commands in this project use **PowerShell 7+** (`pwsh`). Install tools with winget:

```powershell
winget install --id Microsoft.PowerShell -e
winget install --id Python.Python.3.12 -e
winget install --id astral-sh.uv -e
winget install --id Docker.DockerDesktop -e
winget install --id Kubernetes.kind -e
winget install --id Kubernetes.kubectl -e
winget install --id Helm.Helm -e
winget install --id Hashicorp.Terraform -e
winget install --id Google.CloudSDK -e
winget install --id Git.Git -e
winget install --id GitHub.cli -e
```

Verify (open a **new** PowerShell window first so PATH updates load):

```powershell
$checks = 'python --version','uv --version','docker compose version','kind version',
          'kubectl version --client','helm version --short','terraform version',
          'gcloud --version','git --version','gh --version'
foreach ($c in $checks) {
  try { $out = Invoke-Expression $c 2>&1 | Select-Object -First 1; Write-Host "OK   $c -> $out" -ForegroundColor Green }
  catch { Write-Host "MISS $c" -ForegroundColor Red }
}
```

If scripts are blocked, allow local scripts for your user once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## 2. Local (Docker Compose)

Everything runs in containers, so a clean clone needs only Docker Desktop (NFR-01). Stop a locally running API
(port 8000) or mock ERP (port 8100) first, or choose other host ports with `$env:API_PORT` / `$env:ERP_HOST_PORT`.

```powershell
Copy-Item .env.example .env                       # FAKE_LLM=1 needs no key; for real models add OPENAI_API_KEY
.\tasks.ps1 demo                                  # builds both images (tagged with the git commit) and starts:
                                                  # postgres -> seed job -> migrate+ingest job -> mock ERP -> API
Invoke-RestMethod http://localhost:8000/health    # status ok, version.build_sha = your commit
Start-Process http://localhost:8000               # agent console
.\tasks.ps1 stack-down                            # stops the containers; the database volume is kept
```

`.\tasks.ps1 up` still starts only Postgres, for development and tests (`uv run pytest -q`).
Never run `docker compose config` without `--no-interpolate`: it prints resolved values, including keys from `.env`.

## 3. Kubernetes (kind)

```powershell
.\tasks.ps1 images                                # build fde-api:local and fde-mock-erp:local
.\tasks.ps1 kind-up                               # create the cluster "fde" and load both images into it
helm upgrade --install fde deploy/helm/fde-kit --wait --timeout 10m `
  --set engagement=demo-logistics `
  --set-file engagementConfig=engagements/demo-logistics/engagement.yaml
kubectl get pods                                  # fde-api, fde-mock-erp, fde-postgres-0: all Running and Ready
kubectl port-forward svc/fde-api 8000:8000        # leave running; in a second window:
Invoke-RestMethod http://localhost:8000/health
.\tasks.ps1 kind-down                             # deletes the cluster and everything in it
```

The chart's Postgres is for kind only (`postgres.enabled=false` in the cloud). CI runs exactly these steps on every
push (`.github/workflows/ci.yml`, job `containers`), so the chart is tested even when a laptop is short of memory.

## 4. GCP Cloud Run (Terraform)

Who runs this: **the human only** (CLAUDE.md rule 5). It creates billable resources. Expected cost while it exists:
Cloud SQL `db-g1-small` $0.035/h + 10 GiB SSD $0.00233/h = **about $0.037 per hour, $0.90 per day, $27 per 30 days**
(prices from [12-cost-estimate.md](12-cost-estimate.md)); Cloud Run, Artifact Registry and Secret Manager stay inside
their free tiers at demo volume. The single biggest risk is forgetting the teardown in section 7.

### 4.1 One-time setup

```powershell
$ProjectId   = 'your-gcp-project-id'               # replace with the real id
$Region      = 'us-east1'
$StateBucket = "$ProjectId-tfstate"
gcloud auth login
gcloud auth application-default login
gcloud config set project $ProjectId
gcloud billing budgets list --billing-account (gcloud billing projects describe $ProjectId --format 'value(billingAccountName)').Split('/')[-1]   # confirm the $25 budget alert exists
gcloud services enable artifactregistry.googleapis.com cloudresourcemanager.googleapis.com
gcloud storage buckets create "gs://$StateBucket" --location=$Region --uniform-bucket-level-access
gcloud storage buckets update "gs://$StateBucket" --versioning
terraform -chdir=deploy/terraform/gcp init -backend-config="bucket=$StateBucket"
```

### 4.2 Deploy

Images must exist in Artifact Registry before the Cloud Run services can start, so the registry is created first:

```powershell
$ImageTag = git rev-parse --short HEAD
$Me       = gcloud config get-value account        # who may call the API (it is never public, DC-031)
$TfVars   = @("-var=project_id=$ProjectId", "-var=region=$Region", "-var=image_tag=$ImageTag", "-var=api_invokers=[`"user:$Me`"]")

# 1. Registry and APIs only
terraform -chdir=deploy/terraform/gcp apply @TfVars -target=google_artifact_registry_repository.images -target=google_project_service.enabled

# 2. Build and push both images (tag = commit)
$Reg = "$Region-docker.pkg.dev/$ProjectId/fde"
gcloud auth configure-docker "$Region-docker.pkg.dev" --quiet
docker build -f deploy/docker/api.Dockerfile --build-arg BUILD_SHA=$ImageTag -t "$Reg/fde-api:$ImageTag" .
docker build -f deploy/docker/mock-erp.Dockerfile --build-arg BUILD_SHA=$ImageTag -t "$Reg/fde-mock-erp:$ImageTag" .
docker push "$Reg/fde-api:$ImageTag"
docker push "$Reg/fde-mock-erp:$ImageTag"

# 3. Everything else: review the plan, then apply
terraform -chdir=deploy/terraform/gcp plan  @TfVars -out=tfplan
terraform -chdir=deploy/terraform/gcp apply tfplan

# 4. Only for real models: add the OpenAI key as a secret version (Terraform never sees the value).
#    Writing to a temp file avoids PowerShell adding a trailing newline in the pipeline.
$tmp = New-TemporaryFile
[IO.File]::WriteAllText($tmp, $env:OPENAI_API_KEY)
gcloud secrets versions add openai-api-key --data-file=$tmp
Remove-Item $tmp

# 5. Load data, then smoke test THROUGH THE PROXY (the API is not public: Cloud Run checks your Google identity)
.\tasks.ps1 ingest-remote                          # Cloud Run job fde-ingest: migrate, seed, ETL, documents
gcloud run services proxy fde-api --region $Region --port 8080   # leave running; in a second window:
Invoke-RestMethod http://localhost:8080/health     # status ok; approvals_auth true; chat_auth true; build_sha = $ImageTag
.\scripts\smoke.ps1 -Url http://localhost:8080

# 6. The app's own tokens (generated by Terraform; read them when you need them, never paste them into chat or files)
$env:APPROVER_TOKEN = gcloud secrets versions access latest --secret approver-token   # console field "Reviewer token"
$env:CHAT_TOKEN     = gcloud secrets versions access latest --secret chat-token       # console field "Chat token"
```

Expected: `terraform apply` ends with `api_url = "https://fde-api-....run.app"`. Opening that URL directly in a browser
gives **403 Forbidden**: that is correct (DC-031). The demo goes through `http://localhost:8080` from the proxy; to let a
colleague in, add them to `api_invokers` and apply again. Approving a write in the console needs the reviewer token,
chatting needs the chat token.

### 4.3 CI/CD path (after the first manual deploy)

`deploy.yml` builds, pushes and rolls out new images with Workload Identity Federation (no JSON key). It is disabled
until these repository **variables** exist (values from Terraform):

```powershell
gh variable set GCP_PROJECT_ID   --body $ProjectId
gh variable set GCP_REGION       --body $Region
gh variable set GCP_WIF_PROVIDER --body (terraform -chdir=deploy/terraform/gcp output -raw github_wif_provider)
gh variable set GCP_DEPLOY_SA    --body (terraform -chdir=deploy/terraform/gcp output -raw github_deploy_service_account)
gh variable set DEPLOY_ENABLED   --body true
gh workflow run deploy.yml -f confirm=deploy
```

Terraform owns the infrastructure; the workflow only changes images (Terraform ignores image changes, so the two
never fight). The real-model eval is a separate manual workflow: `gh workflow run eval-real.yml` (needs the repository
secret `OPENAI_API_KEY`: `gh secret set OPENAI_API_KEY`).

## 5. Operations
| Task | Command / action |
|---|---|
| View logs | `gcloud run services logs read fde-api --region us-east1` |
| Rollback | Re-deploy previous `image_tag` via `terraform apply`, or shift traffic to previous revision in Cloud Run |
| Rotate OpenAI key | Add new secret version; redeploy; disable old version |
| Re-ingest after doc changes | `.\tasks.ps1 ingest-remote -Engagement demo-logistics` (idempotent) |
| Switch LLM provider | Edit `llm:` in `engagement.yaml`; re-run evals; if embedding model changed, re-ingest |

## 6. Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|
| `/chat` 500, "relation chunks does not exist" | Migrations/ingest not run | `.\tasks.ps1 migrate; .\tasks.ps1 ingest` |
| Answers have no citations | Retrieval empty | Check ingest counts; check embedding model matches index dimension |
| Agent loops until step limit | Tool errors or vague prompt | Inspect trace; check tool error messages returned to the model |
| Cloud Run can't reach Cloud SQL | Missing Cloud SQL Client role / connection annotation | Check service account + `cloud_sql_instance` setting in Terraform |
| CI eval gate fails | Real regression or flaky case | Read report diff; fix or document — never delete cases to pass |

## 7. Teardown (do this after demos)

```powershell
terraform -chdir=deploy/terraform/gcp destroy "-var=project_id=$ProjectId" "-var=region=$Region"
gcloud sql instances list                          # expect: Listed 0 items.
gcloud run services list --region $Region          # expect: no fde-api / fde-mock-erp
gh variable set DEPLOY_ENABLED --body false        # so nobody redeploys by accident
```

Then confirm in the Billing console (Reports, filter by the project) that Cloud SQL charges stop. The state bucket and
the Artifact Registry images left over cost cents; delete them with
`gcloud storage rm -r "gs://$StateBucket"` only after `destroy` succeeded (the state is needed to destroy).
