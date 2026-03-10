resource "google_service_account" "workflows" {
  project      = var.project_id
  account_id   = "precision-genomics-workflows"
  display_name = "Precision Genomics Workflows"
}

resource "google_project_iam_member" "workflows_invoker" {
  project = var.project_id
  role    = "roles/workflows.invoker"
  member  = "serviceAccount:${google_service_account.workflows.email}"
}

resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.workflows.email}"
}

resource "google_workflows_workflow" "biomarker_discovery" {
  name            = "precision-genomics-biomarker-discovery"
  project         = var.project_id
  region          = var.region
  service_account = google_service_account.workflows.id
  source_contents = file("${path.root}/../workflows/definitions/biomarker_discovery.yaml")
}

resource "google_workflows_workflow" "sample_qc" {
  name            = "precision-genomics-sample-qc"
  project         = var.project_id
  region          = var.region
  service_account = google_service_account.workflows.id
  source_contents = file("${path.root}/../workflows/definitions/sample_qc.yaml")
}

resource "google_workflows_workflow" "prompt_optimization" {
  name            = "precision-genomics-prompt-optimization"
  project         = var.project_id
  region          = var.region
  service_account = google_service_account.workflows.id
  source_contents = file("${path.root}/../workflows/definitions/prompt_optimization.yaml")
}

variable "project_id" { type = string }
variable "region" { type = string }
variable "activity_service_url" { type = string }

output "biomarker_discovery_id" { value = google_workflows_workflow.biomarker_discovery.id }
output "sample_qc_id" { value = google_workflows_workflow.sample_qc.id }
output "prompt_optimization_id" { value = google_workflows_workflow.prompt_optimization.id }
