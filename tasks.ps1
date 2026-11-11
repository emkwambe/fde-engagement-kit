#Requires -Version 7.0
<#
.SYNOPSIS
  Task runner for the FDE Engagement Kit (PowerShell replacement for make).

.EXAMPLE
  .\tasks.ps1 help
  .\tasks.ps1 demo -Engagement demo-logistics
  .\tasks.ps1 eval -Engagement demo-logistics

.NOTES
  Tasks marked (Day N) call Python modules that are built on that day of the sprint.
#>
[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateSet('help', 'setup', 'up', 'down', 'migrate', 'seed', 'ingest', 'eval', 'demo',
               'test', 'lint', 'kind-up', 'kind-down', 'ingest-remote', 'check-tools')]
  [string]$Task = 'help',

  [string]$Engagement = 'demo-logistics'
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:ENGAGEMENT = $Engagement

function Invoke-Step([string]$Label, [scriptblock]$Action) {
  Write-Host "==> $Label" -ForegroundColor Cyan
  & $Action
  if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "Step failed: $Label (exit $LASTEXITCODE)" }
}

function Import-DotEnv {
  if (-not (Test-Path .env)) { Write-Warning '.env not found. Run: Copy-Item .env.example .env'; return }
  Get-Content .env | Where-Object { $_ -match '^\s*[^#].*=' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    $value = ($value -replace '\s+#.*$', '').Trim()
    Set-Item -Path "env:$($name.Trim())" -Value $value
  }
}

function Assert-EngagementExists {
  if (-not (Test-Path "engagements/$Engagement/engagement.yaml")) {
    throw "Engagement '$Engagement' not found in engagements/. Copy engagements/_template first."
  }
}

Import-DotEnv

switch ($Task) {
  'help' {
    Get-Help $PSCommandPath -Detailed | Out-Host
    Write-Host @'
Tasks:
  check-tools    Verify required CLIs are installed
  setup          Create .venv and install dependencies with uv          (Day 1)
  up / down      Start / stop the local Docker Compose stack
  migrate        Create database schemas, tables, read-only role        (Day 1)
  seed           Generate synthetic data with fixed seeds                (Day 1)
  ingest         ETL tables + embed documents into pgvector             (Day 1)
  eval           Run the golden-set evaluation, write report            (Day 3)
  demo           up + migrate + seed + ingest + start API at http://localhost:8000/docs
  test / lint    pytest / ruff + mypy
  kind-up/-down  Create / delete the local Kubernetes cluster            (Day 4)
  ingest-remote  Run ingestion as a Cloud Run job                       (Day 4)
'@
  }
  'check-tools' {
    $checks = 'python --version', 'uv --version', 'docker compose version', 'kind version',
              'kubectl version --client', 'helm version --short', 'terraform version',
              'gcloud --version', 'git --version', 'gh --version'
    foreach ($c in $checks) {
      try { $out = Invoke-Expression $c 2>&1 | Select-Object -First 1; Write-Host "OK   $c -> $out" -ForegroundColor Green }
      catch { Write-Host "MISS $c" -ForegroundColor Red }
    }
  }
  'setup'   { Invoke-Step 'Install dependencies' { uv sync } }
  'up'      { Invoke-Step 'Start stack' { docker compose up -d --wait } }
  'down'    { Invoke-Step 'Stop stack'  { docker compose down } }
  'migrate' { Invoke-Step 'Migrate database' { uv run python -m core.db.migrate } }
  'seed'    { Assert-EngagementExists; Invoke-Step "Seed data ($Engagement)" { uv run python -m core.ingest.seed --engagement $Engagement } }
  'ingest'  { Assert-EngagementExists; Invoke-Step "Ingest ($Engagement)"    { uv run python -m core.ingest.run  --engagement $Engagement } }
  'eval'    { Assert-EngagementExists; Invoke-Step "Evaluate ($Engagement)"  { uv run python -m core.evals.run   --engagement $Engagement } }
  'demo' {
    Assert-EngagementExists
    & $PSCommandPath up
    & $PSCommandPath migrate
    & $PSCommandPath seed   -Engagement $Engagement
    & $PSCommandPath ingest -Engagement $Engagement
    Write-Host 'API docs: http://localhost:8000/docs  (Ctrl+C to stop; chat UI arrives Day 3)' -ForegroundColor Green
    Start-Process 'http://localhost:8000/docs'
    uv run uvicorn core.api.main:app --port 8000
  }
  'test' { Invoke-Step 'Run tests' { $env:FAKE_LLM = '1'; uv run pytest -q } }
  'lint' {
    Invoke-Step 'Ruff' { uv run ruff check . }
    Invoke-Step 'Mypy' { uv run mypy core }
  }
  'kind-up' {
    Invoke-Step 'Create kind cluster' { kind create cluster --name fde --wait 120s }
    foreach ($img in 'fde-api:local', 'fde-mock-erp:local', 'fde-ui:local') {
      Invoke-Step "Load $img" { kind load docker-image $img --name fde }
    }
  }
  'kind-down' { Invoke-Step 'Delete kind cluster' { kind delete cluster --name fde } }
  'ingest-remote' {
    Assert-EngagementExists
    Invoke-Step "Cloud Run ingest job ($Engagement)" {
      gcloud run jobs execute fde-ingest --region us-east1 --wait --update-env-vars "ENGAGEMENT=$Engagement"
    }
  }
}
