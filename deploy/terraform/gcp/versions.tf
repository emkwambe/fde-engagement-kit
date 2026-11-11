# Terraform for the FDE Engagement Kit on GCP (D-15). PREPARED AND VALIDATED ONLY: the executor never applies it
# (CLAUDE.md rule 5). The human runs it, with the exact commands in docs/11-deployment-runbook.md section 4.
#
# Remote state lives in a GCS bucket the human creates first (versioned, so a bad apply can be rolled back).
# The bucket name is passed at init time, so no project-specific value is committed:
#   terraform init -backend-config="bucket=<project>-tfstate"
# State contains generated secret VALUES (database passwords, tokens): the bucket must stay private.

terraform {
  required_version = ">= 1.9"

  backend "gcs" {
    prefix = "fde-engagement-kit"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0, < 8.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
