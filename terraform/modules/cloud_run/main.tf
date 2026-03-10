resource "google_cloud_run_v2_service" "api" {
  name     = "precision-genomics-api"
  project  = var.project_id
  location = var.region

  template {
    containers {
      image = "${var.registry_url}/api:latest"

      ports {
        container_port = 8000
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCS_DATA_BUCKET"
        value = var.gcs_data_bucket
      }
      env {
        name  = "GCS_MODEL_BUCKET"
        value = var.gcs_model_bucket
      }
      env {
        name  = "REDIS_URL"
        value = "redis://${var.redis_host}:${var.redis_port}/0"
      }
      env {
        name  = "CLOUD_SQL_INSTANCE"
        value = var.cloud_sql_instance
      }
      env {
        name  = "USE_SECRET_MANAGER"
        value = "true"
      }
      env {
        name  = "PERSIST_MODELS"
        value = "true"
      }
      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.secret_anthropic_id
            version = "latest"
          }
        }
      }
      env {
        name = "DATABASE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = var.secret_db_pass_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }
    }

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }
}

resource "google_cloud_run_v2_service" "mcp_sse" {
  name     = "precision-genomics-mcp-sse"
  project  = var.project_id
  location = var.region

  template {
    containers {
      image = "${var.registry_url}/mcp-sse:latest"

      ports {
        container_port = 8080
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCS_DATA_BUCKET"
        value = var.gcs_data_bucket
      }
      env {
        name  = "GCS_MODEL_BUCKET"
        value = var.gcs_model_bucket
      }
      env {
        name  = "USE_SECRET_MANAGER"
        value = "true"
      }
      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.secret_anthropic_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
      }
    }

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 5
    }
  }
}

resource "google_cloud_run_v2_service" "activity_worker" {
  name     = "precision-genomics-worker"
  project  = var.project_id
  location = var.region

  template {
    containers {
      image = "${var.registry_url}/worker:latest"

      ports {
        container_port = 8081
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCS_DATA_BUCKET"
        value = var.gcs_data_bucket
      }
      env {
        name  = "GCS_MODEL_BUCKET"
        value = var.gcs_model_bucket
      }
      env {
        name  = "REDIS_URL"
        value = "redis://${var.redis_host}:${var.redis_port}/0"
      }
      env {
        name  = "CLOUD_SQL_INSTANCE"
        value = var.cloud_sql_instance
      }
      env {
        name  = "USE_SECRET_MANAGER"
        value = "true"
      }
      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.secret_anthropic_id
            version = "latest"
          }
        }
      }
      env {
        name = "DATABASE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = var.secret_db_pass_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "4"
          memory = "8Gi"
        }
      }
    }

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    timeout = "900s"
  }
}

variable "project_id" { type = string }
variable "region" { type = string }
variable "vpc_connector_id" { type = string }
variable "registry_url" { type = string }
variable "cloud_sql_instance" { type = string }
variable "redis_host" { type = string }
variable "redis_port" { type = number }
variable "gcs_data_bucket" { type = string }
variable "gcs_model_bucket" { type = string }
variable "secret_anthropic_id" { type = string }
variable "secret_db_pass_id" { type = string }

output "api_url" { value = google_cloud_run_v2_service.api.uri }
output "mcp_sse_url" { value = google_cloud_run_v2_service.mcp_sse.uri }
output "activity_worker_url" { value = google_cloud_run_v2_service.activity_worker.uri }
