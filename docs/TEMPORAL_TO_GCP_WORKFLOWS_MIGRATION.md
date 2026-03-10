# Plan: Migrate from Temporal to GCP Workflows

## Context

The platform runs 3 Temporal workflows on a self-managed GCE VM (e2-standard-4, ~$98/month). The rest of the infrastructure is already serverless GCP (Cloud Run, Cloud SQL, GCS, Vertex AI). Migrating to GCP Workflows eliminates the VM, reduces cost to ~$5/month, and simplifies operations by going fully serverless.

The current workflows are medium-complexity sequential pipelines with some fan-out. They don't use Temporal's advanced features (signals, continue-as-new, heartbeats, long-running replay). The features they do use — retries, fan-out, conditional branching, saga compensation, progress tracking — all have GCP Workflows equivalents.

---

## Architecture Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Activity wrapping | Dedicated Cloud Run "activity-worker" service | Separates long-running ML work from user-facing API. Independent scaling. |
| Fan-out/fan-in | GCP Workflows `parallel for` | Native construct, maps directly from `asyncio.gather` |
| Progress tracking | Write to Cloud SQL from each activity endpoint | Already using Cloud SQL; no new service needed |
| Saga compensation | `try/except` blocks in YAML | GCP Workflows native error handling |
| Local development | `LocalWorkflowRunner` calling activity functions directly | Replaces existing mock store pattern; no GCP emulator exists |
| Workflow definitions | YAML files in `workflows/definitions/` | GCP Workflows requires YAML; keep orchestration logic there, business logic in Python |

---

## Implementation Steps

### Step 1: Activity Service (`workflows/activity_service.py`)

Create a FastAPI app exposing all ~20 activities as POST endpoints. Each activity:
- Accepts JSON body with parameters + `workflow_id`
- Calls the existing Python activity logic (stripped of `@activity.defn`)
- Writes progress to a `workflow_progress` Cloud SQL table
- Returns JSON result

**New files:**
- `workflows/activity_service.py` — FastAPI app with `/activities/*` endpoints
- `workflows/progress.py` — `WorkflowExecution` table + `update_progress()` / `get_progress()`
- `Dockerfile.activity-worker` (or repurpose `Dockerfile.worker`)

**Modified files:**
- `workflows/activities/data_activities.py` — Strip `@activity.defn`, remove `HAS_TEMPORAL` guards
- `workflows/activities/ml_activities.py` — Same
- `workflows/activities/claude_activities.py` — Same
- `workflows/activities/dspy_activities.py` — Same
- `workflows/activities/gpu_training_activities.py` — Same

### Step 2: GCP Workflow YAML Definitions

Translate 3 Python workflow classes to YAML:

**New files:**
- `workflows/definitions/biomarker_discovery.yaml` — 7 steps, `parallel for` on impute + feature_select phases
- `workflows/definitions/sample_qc.yaml` — 6 sequential steps, `try/except` with quarantine compensation
- `workflows/definitions/prompt_optimization.yaml` — 5 steps, `switch` for conditional skip on compile failure

Each YAML step calls `http.post` to the activity service URL with retry policy (initial 1s, max 30s, 3 attempts).

### Step 3: Update API Routes

**Modified files:**
- `api/routes/analysis.py` — Replace `_get_temporal_client()` with `_get_workflows_client()`. Use `google.cloud.workflows.executions_v1.ExecutionsClient` to create/get/cancel executions. Query `workflow_progress` table for status. Keep mock store fallback for local dev.
- `api/routes/workflows.py` — Same switchover.
- `workflows/config.py` — Replace `WorkflowConfig(host, namespace, task_queue)` with `WorkflowConfig(project, location, activity_service_url, workflow_ids)`.
- `workflows/schemas.py` — Remove `task_queue` from `WorkflowInfo`, add `execution_name`.

### Step 4: Local Development Runner

**New file:**
- `workflows/local_runner.py` — `LocalWorkflowRunner` with `run_biomarker_discovery()`, `run_sample_qc()`, `run_prompt_optimization()`. Calls activity functions directly via `asyncio.gather` for fan-out. Replaces mock store pattern.

### Step 5: Infrastructure Updates

**Terraform:**
- `terraform/main.tf` — Remove `module "temporal_vm"`, add `module "workflows"`
- Delete `terraform/modules/temporal_vm/`
- Create `terraform/modules/workflows/main.tf` — 3 `google_workflows_workflow` resources, service account with `roles/workflows.invoker` + `roles/run.invoker`
- `terraform/modules/cloud_run/main.tf` — Add activity-worker service (4 vCPU, 8Gi, 900s timeout)

**Docker:**
- `docker-compose.yml` — Remove `temporal` + `temporal-ui` services, add `activity-worker` service on port 8081
- `Dockerfile.worker` — Change CMD from `python -m workflows.worker` to `uvicorn workflows.activity_service:app`; drop `temporal` pip extra

**CI/CD:**
- `.github/workflows/deploy-gcp.yml` — Build/push activity-worker image, deploy to Cloud Run, add `gcloud workflows deploy` steps for 3 YAML files

### Step 6: Cleanup

**Delete:**
- `workflows/worker.py` — No longer needed (no Temporal worker)
- `workflows/biomarker_discovery.py` — Replaced by YAML
- `workflows/sample_qc.py` — Replaced by YAML
- `workflows/prompt_optimization.py` — Replaced by YAML

**Update:**
- `pyproject.toml` — Remove `temporalio` from dependencies, add `google-cloud-workflows` to `gcp` group
- `.env.example` — Replace `TEMPORAL_*` vars with `WORKFLOWS_*` vars
- `core/config.py` — Remove any `temporal_host` references

### Step 7: Update Docs & README

- `README.md` — Replace Temporal references in architecture diagram, project structure, quick start, deployment diagram
- `docs/ARCHITECTURE.md` — Update workflow orchestration section
- `docs/GCP_DEPLOYMENT.md` — Remove Temporal VM section, add GCP Workflows section

### Step 8: Update Tests

- `tests/test_workflows/test_activities.py` — Remove Temporal test setup, test plain async functions
- `tests/test_workflows/test_biomarker_workflow.py` — Test YAML validity, test activity service endpoints
- `tests/test_workflows/test_sample_qc_workflow.py` — Same
- `tests/test_workflows/test_prompt_optimization.py` — Same
- New: `tests/test_workflows/test_activity_service.py` — Integration tests for HTTP endpoints
- New: `tests/test_workflows/test_local_runner.py` — Tests for local runner

---

## What We Lose (and Why It's Fine)

| Temporal Feature | Impact | Mitigation |
|---|---|---|
| Durable replay from checkpoints | Low — activities are 5-30 min, not days | GCP Workflows retries at step level |
| Real-time progress queries | Medium — adds ~100ms latency | Cloud SQL progress table, polled by API |
| Temporal UI | Low | GCP Console has execution history + step details |
| Workflow versioning | Low — only 3 workflows | Git + Terraform deploy |
| Heartbeats | None — not currently used | N/A |

---

## Cost Impact

| Component | Before | After |
|-----------|--------|-------|
| Temporal VM (e2-standard-4) | ~$98/month | $0 |
| GCP Workflows | $0 | ~$1/month |
| Activity Worker (Cloud Run) | $0 | ~$5/month (scales to zero) |
| **Net** | **~$98/month** | **~$6/month** |

---

## Risks

1. **Long-running activities (>15 min):** GPU training activities submit Vertex AI jobs and return immediately — no issue. ML activities (impute, feature select, train) run 5-15 min — within Cloud Run's 900s timeout.
2. **No GCP Workflows emulator:** `LocalWorkflowRunner` provides full local dev coverage.
3. **YAML less expressive than Python:** Keep YAML as thin orchestration only. All logic in Python activity functions.

---

## Verification

1. Run `pytest tests/test_workflows/` — all activity tests pass with plain functions
2. Start activity service locally: `uvicorn workflows.activity_service:app --port 8081`
3. Run local runner: `python -c "from workflows.local_runner import LocalWorkflowRunner; ..."`
4. Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('workflows/definitions/biomarker_discovery.yaml'))"`
5. Deploy to GCP and trigger via API, verify execution completes in GCP Console
6. Check progress tracking via `GET /analyze/{id}/status`

---

## Files Summary

**New (7):**
- `workflows/activity_service.py`
- `workflows/progress.py`
- `workflows/local_runner.py`
- `workflows/definitions/biomarker_discovery.yaml`
- `workflows/definitions/sample_qc.yaml`
- `workflows/definitions/prompt_optimization.yaml`
- `terraform/modules/workflows/main.tf`

**Modified (17):**
- `workflows/activities/data_activities.py`, `ml_activities.py`, `claude_activities.py`, `dspy_activities.py`, `gpu_training_activities.py`
- `workflows/config.py`, `workflows/schemas.py`
- `api/routes/analysis.py`, `api/routes/workflows.py`
- `terraform/main.tf`, `terraform/modules/cloud_run/main.tf`
- `docker-compose.yml`, `Dockerfile.worker`
- `.github/workflows/deploy-gcp.yml`
- `pyproject.toml`, `.env.example`, `core/config.py`

**Deleted (5):**
- `workflows/worker.py`
- `workflows/biomarker_discovery.py`, `sample_qc.py`, `prompt_optimization.py`
- `terraform/modules/temporal_vm/`

**Docs updated (3):**
- `README.md`, `docs/ARCHITECTURE.md`, `docs/GCP_DEPLOYMENT.md`

**Tests updated/created (6):**
- Existing 4 test files updated + 2 new test files
