variable "project_id" {
  description = "GCP project id (never committed: pass with -var or a git-ignored terraform.tfvars)"
  type        = string
}

variable "region" {
  description = "Region for every resource"
  type        = string
  default     = "us-east1"
}

variable "image_tag" {
  description = "Image tag to deploy on FIRST apply (later rollouts come from the deploy workflow; Terraform ignores image changes)"
  type        = string
  default     = "latest"
}

variable "engagement" {
  description = "Engagement folder baked into the image that this deployment serves"
  type        = string
  default     = "demo-logistics"
}

variable "fake_llm" {
  description = "\"1\" = fake models (free); \"0\" = real OpenAI (needs the openai-api-key secret version, costs money)"
  type        = string
  default     = "1"
}

variable "llm_model" {
  description = "Chat model when fake_llm = \"0\""
  type        = string
  default     = "gpt-6-luna"
}

variable "db_tier" {
  description = "Cloud SQL machine tier. db-g1-small = shared core, 1.7 GiB, about $0.035/h (docs/12-cost-estimate.md)"
  type        = string
  default     = "db-g1-small"
}

variable "api_invokers" {
  description = "IAM members allowed to call the API, e.g. [\"user:you@example.com\"]. The API is never public (DC-031)."
  type        = list(string)
  default     = []
}

variable "github_repository" {
  description = "owner/repo allowed to deploy through Workload Identity Federation"
  type        = string
  default     = "emkwambe/fde-engagement-kit"
}
