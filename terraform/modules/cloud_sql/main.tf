resource "google_sql_database_instance" "main" {
  name             = "precision-genomics-pg"
  project          = var.project_id
  region           = var.region
  database_version = "POSTGRES_15"

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"
    disk_size         = 20

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.network_id
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "app" {
  name     = "precision_genomics"
  instance = google_sql_database_instance.main.name
  project  = var.project_id
}

resource "google_sql_user" "app" {
  name     = "app"
  instance = google_sql_database_instance.main.name
  project  = var.project_id
  password = var.db_password
}

variable "project_id" { type = string }
variable "region" { type = string }
variable "network_id" { type = string }
variable "db_password" { type = string; sensitive = true }
variable "db_tier" { type = string; default = "db-custom-2-8192" }

output "connection_name" { value = google_sql_database_instance.main.connection_name }
output "private_ip" { value = google_sql_database_instance.main.private_ip_address }
