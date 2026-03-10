resource "google_artifact_registry_repository" "main" {
  provider      = google-beta
  project       = var.project_id
  location      = var.region
  repository_id = "precision-genomics"
  format        = "DOCKER"
  description   = "Docker images for Precision Genomics Agent Platform"
}

variable "project_id" { type = string }
variable "region" { type = string }

output "registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}"
}
