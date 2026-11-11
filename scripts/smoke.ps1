#Requires -Version 7.0
<#
.SYNOPSIS
  Post-deploy smoke test: health check plus one canned question.
.EXAMPLE
  .\scripts\smoke.ps1 -Url https://fde-api-xxxx.run.app
#>
param([Parameter(Mandatory)][string]$Url)
$ErrorActionPreference = 'Stop'

$health = Invoke-RestMethod "$Url/health" -TimeoutSec 30
if ($health.status -ne 'ok') { throw "Health check failed: $($health | ConvertTo-Json -Compress)" }
Write-Host 'OK   /health' -ForegroundColor Green

$body = @{ thread_id = "smoke-$(Get-Date -Format yyyyMMddHHmmss)"
           message   = 'What SLA credit does a Gold-tier customer get for a 3-day delay?' } | ConvertTo-Json
$resp = Invoke-RestMethod "$Url/chat" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 60
if (-not $resp.citations -or $resp.citations.Count -eq 0) { throw 'Answer returned without citations' }
Write-Host "OK   /chat ($($resp.citations.Count) citations)" -ForegroundColor Green
