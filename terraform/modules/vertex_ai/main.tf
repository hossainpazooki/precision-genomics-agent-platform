resource "google_vertex_ai_metadata_store" "main" {
  provider = google-beta
  project  = var.project_id
  region   = var.region
}

resource "google_vertex_ai_tensorboard" "main" {
  provider     = google-beta
  project      = var.project_id
  region       = var.region
  display_name = "precision-genomics-tensorboard"
}

variable "project_id" { type = string }
variable "region" { type = string }
variable "staging_bucket" { type = string }
variable "experiment_name" { type = string; default = "precision-genomics" }

variable "gpu_machine_types" {
  type    = list(string)
  default = ["a2-highgpu-1g", "a2-highgpu-2g", "g2-standard-4"]
}
