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
```powershell
Copy-Item .env.example .env                       # add OPENAI_API_KEY, or set FAKE_LLM=1
.\tasks.ps1 demo -Engagement demo-logistics
# = docker compose up → migrate → seed → ingest → API at http://localhost:8000/docs (UI arrives Day 3)
.\tasks.ps1 eval -Engagement demo-logistics       # writes evals\reports\<date>-<sha>.md
.\tasks.ps1 down
```

## 3. Kubernetes (kind)
```powershell
.\tasks.ps1 kind-up                               # create cluster, load images
helm upgrade --install fde deploy/helm/fde-kit `
  --set engagement=demo-logistics `
  --set-file engagementConfig=engagements/demo-logistics/engagement.yaml
kubectl get pods -w                               # wait for Ready, then Ctrl+C
kubectl port-forward svc/fde-api 8000:8000        # leave running; use a second window:
Invoke-RestMethod http://localhost:8000/health
.\tasks.ps1 kind-down
```

## 4. GCP Cloud Run (Terraform)
### 4.1 One-time setup
```powershell
$ProjectId   = '<PROJECT_ID>'
$StateBucket = "$ProjectId-tfstate"
gcloud auth login
gcloud auth application-default login
gcloud config set project $ProjectId
gcloud services enable run.googleapis.com sqladmin.googleapis.com `
  artifactregistry.googleapis.com secretmanager.googleapis.com iamcredentials.googleapis.com
gcloud storage buckets create "gs://$StateBucket" --location=us-east1 --uniform-bucket-level-access
Set-Location deploy/terraform/gcp
terraform init -backend-config="bucket=$StateBucket"
```

### 4.2 Deploy
```powershell
$ImageTag = git rev-parse --short HEAD
$TfVars   = @("-var=project_id=$ProjectId", '-var=region=us-east1', "-var=image_tag=$ImageTag")
terraform plan  @TfVars
terraform apply @TfVars

# Add the OpenAI key as a secret version (Terraform creates the secret, not the value).
# Writing to a temp file avoids PowerShell adding a trailing newline in the pipeline.
$tmp = New-TemporaryFile
[IO.File]::WriteAllText($tmp, $env:OPENAI_API_KEY)
gcloud secrets versions add openai-api-key --data-file=$tmp
Remove-Item $tmp

Set-Location ../../..
.\tasks.ps1 ingest-remote -Engagement demo-logistics      # Cloud Run job
$ApiUrl = terraform -chdir=deploy/terraform/gcp output -raw api_url
.\scripts\smoke.ps1 -Url $ApiUrl
```

### 4.3 CI/CD path (normal)
PR → checks + eval gate → merge to `main` → build & push image to Artifact Registry → `terraform apply` with new `image_tag` → smoke test. GitHub authenticates to GCP with Workload Identity Federation.

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
terraform -chdir=deploy/terraform/gcp destroy "-var=project_id=$ProjectId"
```
Confirm in Billing that Cloud SQL is gone.
