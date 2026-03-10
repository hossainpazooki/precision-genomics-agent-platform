resource "google_secret_manager_secret" "anthropic_key" {
  secret_id = "ANTHROPIC_API_KEY"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "anthropic_key" {
  secret      = google_secret_manager_secret.anthropic_key.id
  secret_data = var.anthropic_api_key
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "DATABASE_PASSWORD"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

variable "project_id" { type = string }
variable "anthropic_api_key" { type = string; sensitive = true }
variable "db_password" { type = string; sensitive = true }

output "anthropic_key_secret_id" { value = google_secret_manager_secret.anthropic_key.secret_id }
output "db_password_secret_id" { value = google_secret_manager_secret.db_password.secret_id }
