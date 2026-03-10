# GCP Deployment Guide

This document covers deploying the Precision Genomics Agent Platform to Google Cloud Platform using Terraform, Cloud Run, GCP Workflows, and Vertex AI.

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and authenticated
- Terraform >= 1.5
- A GCP project with billing enabled
- APIs enabled: Cloud Run, Cloud SQL, Memorystore, Secret Manager, Artifact Registry, Vertex AI, Workflows, VPC Access

Enable all required APIs:
```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  workflows.googleapis.com \
  workflowexecutions.googleapis.com \
  vpcaccess.googleapis.com \
  servicenetworking.googleapis.com
```

## Architecture Overview

```
                    Internet
                       |
              Cloud Run (API)  --- Cloud Run (MCP SSE)
                   |                     |
          Serverless VPC Connector
           /        |         \
     Cloud SQL   Memorystore   Cloud Run (Activity Worker)
    (Postgres 15)  (Redis 7)         |
                               GCP Workflows
                            (3 workflow definitions)
```

- **Cloud Run API**: FastAPI service (`Dockerfile`)
- **Cloud Run MCP SSE**: MCP server with SSE transport (`Dockerfile.mcp`)
- **Cloud Run Activity Worker**: Activity service (`Dockerfile.worker`) — executes ML and data activities
- **Cloud SQL**: PostgreSQL 15 with private IP
- **Memorystore**: Redis 7 for caching
- **GCP Workflows**: 3 serverless workflow definitions (biomarker discovery, sample QC, prompt optimization)
- **Vertex AI**: Experiment tracking, model registry, custom training jobs
- **GCS**: Data bucket, model bucket, eval fixtures bucket
- **Secret Manager**: ANTHROPIC_API_KEY, DATABASE_PASSWORD

## Terraform Deployment

### 1. Configure variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 2. Initialize and apply

```bash
terraform init
terraform plan
terraform apply
```

### 3. Outputs

After apply, Terraform outputs:
- `api_url` — Cloud Run API endpoint
- `mcp_sse_url` — Cloud Run MCP SSE endpoint
- `activity_worker_url` — Cloud Run Activity Worker endpoint
- `cloud_sql_connection_name` — For Cloud SQL Proxy
- `redis_host` — Memorystore Redis IP
- `registry_url` — Artifact Registry URL

## Environment Variable Mapping

| Local (.env)         | GCP Equivalent                  |
|---------------------|---------------------------------|
| `DATABASE_URL`      | Cloud SQL via IAM auth connector |
| `REDIS_URL`         | `redis://<memorystore_host>:6379/0` |
| `ANTHROPIC_API_KEY` | Secret Manager                  |
| `DATA_DIR`          | GCS data bucket                 |

GCP-specific env vars set on Cloud Run:
- `GCP_PROJECT_ID`
- `GCS_DATA_BUCKET`, `GCS_MODEL_BUCKET`
- `CLOUD_SQL_INSTANCE`
- `USE_SECRET_MANAGER=true`
- `PERSIST_MODELS=true`
- `REGISTER_VERTEX_MODELS=true`

Workflow-specific env vars:
- `WORKFLOWS_PROJECT` — GCP project ID
- `WORKFLOWS_LOCATION` — Region (default: `us-central1`)
- `WORKFLOWS_ACTIVITY_SERVICE_URL` — Activity worker Cloud Run URL

## GCP Workflows

Three workflow definitions are deployed to GCP Workflows:

| Workflow | YAML Source | Steps | Features |
|----------|-------------|-------|----------|
| `precision-genomics-biomarker-discovery` | `workflows/definitions/biomarker_discovery.yaml` | 7 | `parallel for` fan-out on modalities |
| `precision-genomics-sample-qc` | `workflows/definitions/sample_qc.yaml` | 6 | `try/except` saga compensation |
| `precision-genomics-prompt-optimization` | `workflows/definitions/prompt_optimization.yaml` | 5 | `switch` on compile failure |

Each workflow step calls the Activity Worker service via HTTP POST with retry policies.

### Deploy workflows manually

```bash
gcloud workflows deploy precision-genomics-biomarker-discovery \
  --location us-central1 \
  --source workflows/definitions/biomarker_discovery.yaml

gcloud workflows deploy precision-genomics-sample-qc \
  --location us-central1 \
  --source workflows/definitions/sample_qc.yaml

gcloud workflows deploy precision-genomics-prompt-optimization \
  --location us-central1 \
  --source workflows/definitions/prompt_optimization.yaml
```

### Execute a workflow

```bash
gcloud workflows run precision-genomics-biomarker-discovery \
  --location us-central1 \
  --data='{"dataset":"train","target":"msi","modalities":["proteomics","rnaseq"],"n_top_features":30,"activity_service_url":"https://precision-genomics-worker-xxxxx-uc.a.run.app","workflow_id":"biomarker-manual-001"}'
```

## CI/CD Setup

The pipeline (`.github/workflows/deploy-gcp.yml`) uses Workload Identity Federation and is gated on the CI workflow passing.

### Setup steps:

1. Create a Workload Identity Pool and Provider for GitHub Actions
2. Create a service account with roles:
   - `roles/run.admin`
   - `roles/artifactregistry.writer`
   - `roles/secretmanager.secretAccessor`
   - `roles/iam.serviceAccountUser`
   - `roles/workflows.admin`
3. Add repository secrets:
   - `GCP_PROJECT_ID`
   - `GCP_WORKLOAD_IDENTITY_PROVIDER`
   - `GCP_SERVICE_ACCOUNT`

The deploy workflow triggers only when the CI workflow succeeds on `main`. It builds and deploys all three Cloud Run services and all three GCP Workflow definitions.

## Vertex AI

### Experiments
Experiment tracking is automatic when `GCP_PROJECT_ID` and `VERTEX_AI_EXPERIMENT_NAME` are set. View experiments in the GCP Console under Vertex AI > Experiments.

### Model Registry
Trained models are automatically registered when `REGISTER_VERTEX_MODELS=true`. View them under Vertex AI > Model Registry.

### Custom Training Jobs
Submit training jobs using:
```python
from core.vertex_training import submit_training_job
submit_training_job(
    dataset_uri="gs://your-bucket/data/train_pro.tsv",
    target="msi",
    project="your-project-id",
    staging_bucket="gs://your-bucket",
)
```

## Monitoring

- **Cloud Run metrics**: GCP Console > Cloud Run > Service details
- **GCP Workflows**: GCP Console > Workflows > Execution history
- **Cloud SQL**: GCP Console > SQL > Instance details > Monitoring
- **Structured logs**: GCP Console > Logging > Logs Explorer
  - Filter: `resource.type="cloud_run_revision"`
- **Vertex AI experiments**: GCP Console > Vertex AI > Experiments

## Local Development

Local dev is unaffected. All GCP features are gated by optional config:
```bash
# Local mode (default)
docker-compose up -d
uvicorn api.main:app --reload
python -m mcp_server.server  # stdio transport
```

When GCP config fields are unset (`None`/`False`), the platform uses the `LocalWorkflowRunner` which calls activity functions directly without any cloud dependency.
