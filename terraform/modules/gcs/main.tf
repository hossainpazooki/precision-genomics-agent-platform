resource "google_storage_bucket" "data" {
  name     = "${var.project_id}-genomics-data"
  project  = var.project_id
  location = var.region

  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }
}

resource "google_storage_bucket" "models" {
  name     = "${var.project_id}-genomics-models"
  project  = var.project_id
  location = var.region

  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 5
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "eval_fixtures" {
  name     = "${var.project_id}-genomics-eval-fixtures"
  project  = var.project_id
  location = var.region

  uniform_bucket_level_access = true
  force_destroy               = false
}

variable "project_id" { type = string }
variable "region" { type = string }

output "data_bucket_name" { value = google_storage_bucket.data.name }
output "model_bucket_name" { value = google_storage_bucket.models.name }
output "eval_fixtures_bucket_name" { value = google_storage_bucket.eval_fixtures.name }
