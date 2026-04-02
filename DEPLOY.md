# Precision Genomics — GCP Deployment State

**Date:** 2026-03-12
**GCP Project:** `prec-genomics-agent` (project number: `677590965589`)
**Region:** `us-central1`
**Billing Account:** `01922E-FF924F-B87B2A`

---

## Completed

### Phase 1: GCP Project Setup
- Project created and billing linked
- All required APIs enabled (Cloud Run, Cloud SQL, Redis, Secret Manager, Artifact Registry, Vertex AI, Workflows, VPC Access, Compute, etc.)

### Phase 2: Terraform Pass 1 — Infrastructure (19 resources)
- VPC + VPC Access Connector (`module.networking`)
- Cloud SQL PostgreSQL 15 instance `precision-genomics-pg` (`module.cloud_sql`)
- Memorystore Redis 1GB BASIC (`module.memorystore`)
- 3 GCS buckets (`module.gcs`)
- Artifact Registry repo `precision-genomics` (`module.artifact_registry`)
- Secret Manager secrets: `ANTHROPIC_API_KEY`, `DATABASE_PASSWORD` (`module.secret_manager`)
- Vertex AI Tensorboard (`module.vertex_ai`)

### Phase 3: Docker Images Built & Pushed
All three images pushed to `us-central1-docker.pkg.dev/prec-genomics-agent/precision-genomics/`:
- `api:latest`
- `worker:latest`
- `mcp-sse:latest`

### Phase 5 (moved up): Secret Manager IAM
Granted `roles/secretmanager.secretAccessor` to `677590965589-compute@developer.gserviceaccount.com` on both secrets.

### Bug Fixes Applied (not yet committed)
1. **Vertex AI metadata store** — removed `google_vertex_ai_metadata_store` resource from `terraform/modules/vertex_ai/main.tf` (google-beta provider bug causes perpetual create/destroy cycle)
2. **Biomarker workflow YAML** — fixed `workflows/definitions/biomarker_discovery.yaml`: initialized `imputation_results` and `feature_panels` as empty lists, added `collect_imputation` and `collect_features` assign steps in parallel loop
3. **Terraform semicolons** — expanded single-line variable blocks in `cloud_sql/main.tf`, `secret_manager/main.tf`, `vertex_ai/main.tf` (done in earlier session)

### Phase 4: Terraform Pass 2 — Cloud Run & Workflows (4 added, 3 replaced)
- Cloud Run API: `https://precision-genomics-api-dwl572akmq-uc.a.run.app`
- Cloud Run Worker: `https://precision-genomics-worker-dwl572akmq-uc.a.run.app`
- Cloud Run MCP SSE: `https://precision-genomics-mcp-sse-dwl572akmq-uc.a.run.app`
- 3 GCP Workflows: biomarker-discovery, sample-qc, prompt-optimization

### Phase 6: Health Checks Verified
All three services returning healthy (requires auth token):
- API: `{"status":"healthy","version":"0.1.0"}`
- Worker: `{"status":"ok"}` — 20 activity handlers registered
- MCP SSE: `{"status":"healthy","transport":"sse"}`

---

## Authentication
Services require authentication (no public access). Use:
```bash
curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" <URL>/health
```

## Useful Commands

```bash
# List Cloud Run services
gcloud run services list --region=us-central1 --project=prec-genomics-agent

# Get all Terraform outputs
cd terraform && terraform output

# Health checks (with auth)
TOKEN=$(gcloud auth print-identity-token)
curl -s -H "Authorization: Bearer $TOKEN" "https://precision-genomics-api-dwl572akmq-uc.a.run.app/health"
curl -s -H "Authorization: Bearer $TOKEN" "https://precision-genomics-worker-dwl572akmq-uc.a.run.app/health"
curl -s -H "Authorization: Bearer $TOKEN" "https://precision-genomics-mcp-sse-dwl572akmq-uc.a.run.app/health"

# List workflows
gcloud workflows list --location=us-central1 --project=prec-genomics-agent
```

## Rollback

```bash
# Tear down all infrastructure
cd terraform && terraform destroy

# Nuclear option — delete entire project
gcloud projects delete prec-genomics-agent
```

## Estimated Monthly Cost
| Service | Estimate |
|---------|----------|
| Cloud SQL (db-custom-2-8192) | ~$50-70 |
| Memorystore Redis (1GB BASIC) | ~$35 |
| Cloud Run (API + Worker scale to 0) | pay-per-use |
| Cloud Run (MCP SSE min 1 instance) | ~$15-25 |
| **Total baseline** | **~$100-130** |
