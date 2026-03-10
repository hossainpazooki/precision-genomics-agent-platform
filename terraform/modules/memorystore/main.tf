resource "google_redis_instance" "main" {
  name           = "precision-genomics-redis"
  project        = var.project_id
  region         = var.region
  tier           = "BASIC"
  memory_size_gb = 1
  redis_version  = "REDIS_7_0"

  authorized_network = var.network_id

  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }
}

variable "project_id" { type = string }
variable "region" { type = string }
variable "network_id" { type = string }

output "host" { value = google_redis_instance.main.host }
output "port" { value = google_redis_instance.main.port }
