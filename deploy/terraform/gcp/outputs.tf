output "api_url" {
  description = "Public HTTPS URL of the agent API and console"
  value       = google_cloud_run_v2_service.api.uri
}

output "erp_url" {
  value = google_cloud_run_v2_service.erp.uri
}

output "registry" {
  description = "Push images here: <registry>/fde-api:<tag>"
  value       = local.registry
}

output "github_wif_provider" {
  description = "Repository variable GCP_WIF_PROVIDER for .github/workflows/deploy.yml"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_deploy_service_account" {
  description = "Repository variable GCP_DEPLOY_SA"
  value       = google_service_account.deploy.email
}

output "sql_connection_name" {
  value = google_sql_database_instance.db.connection_name
}
