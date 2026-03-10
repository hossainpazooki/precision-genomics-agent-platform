terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# --- Networking ---
module "networking" {
  source     = "./modules/networking"
  project_id = var.project_id
  region     = var.region
}

# --- Cloud SQL (PostgreSQL 15) ---
module "cloud_sql" {
  source            = "./modules/cloud_sql"
  project_id        = var.project_id
  region            = var.region
  network_id        = module.networking.network_id
  db_password       = var.db_password
  db_tier           = var.db_tier
}

# --- Memorystore (Redis 7) ---
module "memorystore" {
  source     = "./modules/memorystore"
  project_id = var.project_id
  region     = var.region
  network_id = module.networking.network_id
}

# --- GCS Buckets ---
module "gcs" {
  source     = "./modules/gcs"
  project_id = var.project_id
  region     = var.region
}

# --- Artifact Registry ---
module "artifact_registry" {
  source     = "./modules/artifact_registry"
  project_id = var.project_id
  region     = var.region
}

# --- Secret Manager ---
module "secret_manager" {
  source          = "./modules/secret_manager"
  project_id      = var.project_id
  anthropic_api_key = var.anthropic_api_key
  db_password     = var.db_password
}

# --- Cloud Run (API + MCP SSE) ---
module "cloud_run" {
  source              = "./modules/cloud_run"
  project_id          = var.project_id
  region              = var.region
  vpc_connector_id    = module.networking.vpc_connector_id
  registry_url        = module.artifact_registry.registry_url
  cloud_sql_instance  = module.cloud_sql.connection_name
  redis_host          = module.memorystore.host
  redis_port          = module.memorystore.port
  gcs_data_bucket     = module.gcs.data_bucket_name
  gcs_model_bucket    = module.gcs.model_bucket_name
  secret_anthropic_id = module.secret_manager.anthropic_key_secret_id
  secret_db_pass_id   = module.secret_manager.db_password_secret_id
}

# --- Vertex AI ---
module "vertex_ai" {
  source          = "./modules/vertex_ai"
  project_id      = var.project_id
  region          = var.region
  staging_bucket  = module.gcs.model_bucket_name
  experiment_name = var.vertex_ai_experiment_name
}

# --- GCP Workflows ---
module "workflows" {
  source             = "./modules/workflows"
  project_id         = var.project_id
  region             = var.region
  activity_service_url = module.cloud_run.activity_worker_url
}
