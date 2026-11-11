# What this creates (and why), cheapest settings that still work:
#   APIs .................. the services below must be switched on in a new project
#   Artifact Registry ..... private Docker repository for fde-api and fde-mock-erp
#   Cloud SQL ............. Postgres 16 (pgvector is an extension available on Cloud SQL), smallest shared-core tier, no HA
#   Secret Manager ........ DB URLs, ERP token, admin token (generated here) + the OpenAI key (VALUE added by hand)
#   Service accounts ...... runtime (what the containers run as) and deploy (what GitHub Actions acts as)
#   Cloud Run ............. api + mock-erp services (min instances 0 = no idle cost), ingest job
#   Workload Identity ..... GitHub OIDC -> deploy SA, only for this repository: no long-lived JSON key anywhere (T-08)

locals {
  registry   = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
  api_image  = "${local.registry}/fde-api:${var.image_tag}"
  erp_image  = "${local.registry}/fde-mock-erp:${var.image_tag}"
  sql_socket = "/cloudsql/${google_sql_database_instance.db.connection_name}"
  services = [
    "run.googleapis.com", "sqladmin.googleapis.com", "artifactregistry.googleapis.com", "secretmanager.googleapis.com",
    "iam.googleapis.com", "iamcredentials.googleapis.com", "sts.googleapis.com",
  ]
}

resource "google_project_service" "enabled" {
  for_each           = toset(local.services)
  service            = each.value
  disable_on_destroy = false # turning APIs off on destroy can break other things in the project
}

# ------------------------------------------------------------------------------------------------ registry
resource "google_artifact_registry_repository" "images" {
  repository_id = "fde"
  format        = "DOCKER"
  location      = var.region
  description   = "FDE Engagement Kit images"
  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions { keep_count = 10 } # storage beyond 0.5 GiB costs money
  }
  depends_on = [google_project_service.enabled]
}

# ------------------------------------------------------------------------------------------------ database
resource "google_sql_database_instance" "db" {
  name                = "fde-postgres"
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = false # so `terraform destroy` really removes the biggest cost item; turn on for real data

  settings {
    tier              = var.db_tier
    edition           = "ENTERPRISE" # shared-core tiers exist only in the Enterprise edition
    availability_type = "ZONAL"      # no HA: demo scale (scope statement section 4)
    disk_type         = "PD_SSD"
    disk_size         = 10
    disk_autoresize   = false
    backup_configuration {
      enabled = true
      backup_retention_settings { retained_backups = 7 }
    }
    ip_configuration {
      ipv4_enabled = true # public IP but NO authorized networks: only the Cloud SQL connector (IAM-checked) gets in
      ssl_mode     = "ENCRYPTED_ONLY"
    }
  }
  depends_on = [google_project_service.enabled]
}

resource "google_sql_database" "fde" {
  name     = "fde"
  instance = google_sql_database_instance.db.name
}

resource "random_password" "db" {
  length  = 32
  special = false # goes into a URL; letters and digits avoid escaping problems
}

resource "random_password" "agent_ro" {
  length  = 32
  special = false
}

resource "google_sql_user" "fde" {
  name     = "fde"
  instance = google_sql_database_instance.db.name
  password = random_password.db.result
}

# ------------------------------------------------------------------------------------------------ secrets
resource "random_password" "erp_token" {
  length  = 40
  special = false
}

resource "random_password" "admin_token" {
  length  = 40
  special = false
}

locals {
  generated_secrets = {
    "database-url"          = "postgresql://fde:${random_password.db.result}@/fde?host=${local.sql_socket}"
    "agent-ro-password"     = random_password.agent_ro.result
    "agent-ro-database-url" = "postgresql://agent_ro:${random_password.agent_ro.result}@/fde?host=${local.sql_socket}"
    "erp-api-token"         = random_password.erp_token.result
    "admin-token"           = random_password.admin_token.result
  }
}

resource "google_secret_manager_secret" "generated" {
  for_each  = local.generated_secrets
  secret_id = each.key
  replication {
    auto {}
  }
  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "generated" {
  for_each    = local.generated_secrets
  secret      = google_secret_manager_secret.generated[each.key].id
  secret_data = each.value
}

# The OpenAI key: Terraform creates the empty secret; the human adds the value (runbook 4.2), so it never enters state.
resource "google_secret_manager_secret" "openai" {
  secret_id = "openai-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.enabled]
}

# ------------------------------------------------------------------------------------------------ identities
resource "google_service_account" "runtime" {
  account_id   = "fde-runtime"
  display_name = "FDE kit runtime (Cloud Run services and jobs)"
}

resource "google_project_iam_member" "runtime_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client" # connect through the Cloud SQL connector; nothing else project-wide
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_generated" {
  for_each  = google_secret_manager_secret.generated
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor" # per secret, not project-wide (least privilege)
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_openai" {
  secret_id = google_secret_manager_secret.openai.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_service_account" "deploy" {
  account_id   = "fde-deploy"
  display_name = "FDE kit deploy (GitHub Actions via Workload Identity Federation)"
}

resource "google_artifact_registry_repository_iam_member" "deploy_push" {
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_project_iam_member" "deploy_run" {
  project = var.project_id
  role    = "roles/run.developer" # roll out new revisions; cannot change IAM policies
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_service_account_iam_member" "deploy_acts_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser" # needed to deploy a revision that runs as the runtime SA
  member             = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  depends_on                = [google_project_service.enabled]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  # Only tokens minted for THIS repository are accepted, whatever the workflow says.
  attribute_condition = "assertion.repository == \"${var.github_repository}\""
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_impersonates_deploy" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

# ------------------------------------------------------------------------------------------------ Cloud Run
resource "google_cloud_run_v2_service" "erp" {
  name                = "fde-mock-erp"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL" # the API calls it over HTTPS; the app checks its own bearer token

  template {
    service_account = google_service_account.runtime.email
    scaling {
      min_instance_count = 0 # scale to zero: no cost while idle
      max_instance_count = 1 # tickets live in the container's memory/disk: one instance keeps them consistent
    }
    containers {
      image = local.erp_image
      ports { container_port = 8100 }
      resources {
        limits   = { cpu = "1", memory = "512Mi" }
        cpu_idle = true # CPU only while a request is being served (request-based billing)
      }
      env {
        name = "ERP_API_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.generated["erp-api-token"].secret_id
            version = "latest"
          }
        }
      }
      startup_probe {
        http_get { path = "/health" }
      }
    }
  }
  lifecycle {
    ignore_changes = [template[0].containers[0].image, client, client_version] # images roll out via deploy.yml
  }
  depends_on = [google_secret_manager_secret_version.generated, google_secret_manager_secret_iam_member.runtime_generated]
}

locals {
  # Environment shared by the API service and the ingest job. Secrets are referenced, never copied into the config.
  plain_env = {
    ENGAGEMENT           = var.engagement
    FAKE_LLM             = var.fake_llm
    LLM_MODEL            = var.llm_model
    ERP_API_URL          = google_cloud_run_v2_service.erp.uri
    OTEL_TRACES_EXPORTER = "console" # stdout -> Cloud Logging
  }
  secret_env = {
    DATABASE_URL          = google_secret_manager_secret.generated["database-url"].secret_id
    AGENT_RO_PASSWORD     = google_secret_manager_secret.generated["agent-ro-password"].secret_id
    AGENT_RO_DATABASE_URL = google_secret_manager_secret.generated["agent-ro-database-url"].secret_id
    ERP_API_TOKEN         = google_secret_manager_secret.generated["erp-api-token"].secret_id
    ADMIN_TOKEN           = google_secret_manager_secret.generated["admin-token"].secret_id
    OPENAI_API_KEY        = google_secret_manager_secret.openai.secret_id
  }
}

resource "google_cloud_run_v2_service" "api" {
  name                = "fde-api"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.runtime.email
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
    volumes {
      name = "cloudsql"
      cloud_sql_instance { instances = [google_sql_database_instance.db.connection_name] }
    }
    containers {
      image = local.api_image
      ports { container_port = 8000 }
      resources {
        limits   = { cpu = "1", memory = "1Gi" }
        cpu_idle = true
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
      dynamic "env" {
        for_each = local.plain_env
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
      startup_probe {
        http_get { path = "/health" }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 12
      }
      liveness_probe {
        http_get { path = "/health" }
        period_seconds = 30
      }
    }
  }
  lifecycle {
    ignore_changes = [template[0].containers[0].image, client, client_version]
  }
  depends_on = [google_project_iam_member.runtime_sql, google_secret_manager_secret_iam_member.runtime_generated,
  google_secret_manager_secret_iam_member.runtime_openai]
}

# Ingestion as a one-off job (`.\tasks.ps1 ingest-remote`): migrate, seed, ETL and documents, then exit.
resource "google_cloud_run_v2_job" "ingest" {
  name                = "fde-ingest"
  location            = var.region
  deletion_protection = false

  template {
    task_count = 1
    template {
      service_account = google_service_account.runtime.email
      max_retries     = 0 # a failed ingest is investigated, not repeated blindly
      timeout         = "900s"
      volumes {
        name = "cloudsql"
        cloud_sql_instance { instances = [google_sql_database_instance.db.connection_name] }
      }
      containers {
        image   = local.api_image
        command = ["sh", "-c", "python -m core.db.migrate && python -m core.ingest.seed && python -m core.ingest.run"]
        resources {
          limits = { cpu = "1", memory = "1Gi" }
        }
        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
        dynamic "env" {
          for_each = local.plain_env
          content {
            name  = env.key
            value = env.value
          }
        }
        dynamic "env" {
          for_each = local.secret_env
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
      }
    }
  }
  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image, client, client_version]
  }
  depends_on = [google_project_iam_member.runtime_sql, google_secret_manager_secret_iam_member.runtime_generated]
}

# Public demo endpoints (unauthenticated invoke). The API's admin routes still need ADMIN_TOKEN, and the ERP checks its
# own bearer token. An organisation policy (domain-restricted sharing) may forbid allUsers: then drop these two and use
# `gcloud run services proxy` for the demo.
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "erp_public" {
  name     = google_cloud_run_v2_service.erp.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
