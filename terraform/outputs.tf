output "api_url" {
  description = "Cloud Run API service URL"
  value       = module.cloud_run.api_url
}

output "mcp_sse_url" {
  description = "Cloud Run MCP SSE service URL"
  value       = module.cloud_run.mcp_sse_url
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = module.cloud_sql.connection_name
}

output "cloud_sql_private_ip" {
  description = "Cloud SQL private IP"
  value       = module.cloud_sql.private_ip
}

output "redis_host" {
  description = "Memorystore Redis host"
  value       = module.memorystore.host
}

output "gcs_data_bucket" {
  description = "GCS data bucket name"
  value       = module.gcs.data_bucket_name
}

output "gcs_model_bucket" {
  description = "GCS model bucket name"
  value       = module.gcs.model_bucket_name
}

output "registry_url" {
  description = "Artifact Registry URL"
  value       = module.artifact_registry.registry_url
}

output "activity_worker_url" {
  description = "Cloud Run Activity Worker URL"
  value       = module.cloud_run.activity_worker_url
}

output "biomarker_discovery_workflow_id" {
  description = "GCP Workflows biomarker discovery workflow ID"
  value       = module.workflows.biomarker_discovery_id
}

output "sample_qc_workflow_id" {
  description = "GCP Workflows sample QC workflow ID"
  value       = module.workflows.sample_qc_id
}

output "prompt_optimization_workflow_id" {
  description = "GCP Workflows prompt optimization workflow ID"
  value       = module.workflows.prompt_optimization_id
}
