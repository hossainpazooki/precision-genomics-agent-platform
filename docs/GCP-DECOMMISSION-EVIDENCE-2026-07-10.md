# GCP live-run capture + partial decommission — evidence (2026-07-10)

**Executed:** 2026-07-11 UTC (evening 2026-07-10 local, America). Project `prec-genomics-agent`,
region `us-central1`. Operator-authorized scope: **cut the always-on trio; keep everything else.**

## Headline
The GCP deployment behind this repo is **the precision-genomics biomarker platform**, NOT the
CLUE label-correction closed loop. `upstream-label-correction` (CLUE) is the label-correction slice
*extracted from* this platform (cf. git log "extract infra from API repo"). The `passed-vs-true-demo`
depends on **none** of this infra — it replays committed artifacts. So there was **no live CLUE loop
to capture**; the live run below exercises the genomics platform, recorded as "the platform was real
and ran on this date," not as anything the demo relies on.

## 1. Deployed identity (captured BEFORE teardown — read-only)
Three Cloud Run services, all single-revision, deployed 2026-03-13, images built 2026-03-12:

| Service | Revision | Image |
|---|---|---|
| precision-genomics-api | `precision-genomics-api-00001-qvn` | `…/precision-genomics/api:latest` |
| precision-genomics-worker | `precision-genomics-worker-00001-v72` | `…/precision-genomics/worker:latest` |
| precision-genomics-mcp-sse | `precision-genomics-mcp-sse-00001-5wf` | `…/precision-genomics/mcp-sse:latest` |

API image immutable digest (`:latest`): **`sha256:a03babb21ad1d61f6a24dfc405ed1a9eb242e5c94769d7ed2362683f95865f21`** (created 2026-03-12T23:24:21Z).
API self-reported `version: 0.1.0`, `/health` → `{"status":"healthy"}`.
API route map (genomics analysis, no CLUE/intent endpoint): `/analyze/biomarkers`,
`/analyze/sample-qc`, `/analyze/{workflow_id}/{status,report}`, `/biomarkers/panels`,
`/biomarkers/{panel_id}/features`, `/workflows/run`, `/workflows/{workflow_id}/{status,cancel}`, `/health`.

## 2. Live run (dated evidence — genuinely executed, not canned)
- **Request:** `POST /analyze/biomarkers` `{"dataset":"train","target":"msi","modalities":["proteomics"],"n_top_features":5,"cv_folds":2}` (auth: gcloud identity token).
- **Response (HTTP 200):** `{"workflow_id":"biomarker-f7727f587553","status":"pending","message":"Workflow queued (using local runner)"}`.
- **Status endpoint confirmed live tracking:** `{"workflow_id":"biomarker-f7727f587553","workflow_type":"biomarker_discovery","status":"pending","started_at":"2026-07-11T02:07:59.365617+00:00"}`.
- **Refute-the-canned check:** the `workflow_id` was freshly minted and unique to this call, and
  `started_at` matched request time to the second — a canned static response would carry neither.
- **HONEST LIMIT — NOT overclaimed:** the job stayed `pending` across ~90s of polling and did
  **not** reach `completed` in-window (no report captured). Consistent with a single-revision,
  idle-since-March deployment whose async worker is dormant/scale-to-zero. **Evidence proves the
  platform is live and accepted+tracked a real, uniquely-identified biomarker-discovery job — it
  does NOT prove a completed run.** Do not describe this as "completed a genomics analysis."

## 3. Cost-bearing inventory at capture time
| Resource | Spec | ~Monthly (resource estimate) |
|---|---|---|
| Cloud SQL `precision-genomics-pg` | db-custom-2-8192, PG15, RUNNABLE | ~$100–130 (dominant) |
| Redis `precision-genomics-redis` | BASIC 1GB | ~$35–50 |
| VPC connector `precision-genomics-vpc` | e2-micro, min 2 | ~$10–15 |
| Cloud Run ×3 | scale-to-zero | ~$0 idle |
| Artifact Registry `precision-genomics` | DOCKER, 4.86 GB | ~$0.50 |
| GCS ×4 (`…-data`, `…-eval-fixtures`, `…-models`, Vertex auto) + Secrets ×2 | | negligible |

Exact billing NOT pulled — CLI can't itemize without a BigQuery billing export; figures are
resource-based estimates. Handoff's ~$270–325/mo was a higher guess; measured resources sum lower.

## 4. Teardown executed (reconciled from operator's 3 answers: trio only / stop DB / capture first)
| Action | Command | Result (exit) |
|---|---|---|
| **Stop** Cloud SQL (reversible) | `gcloud sql instances patch precision-genomics-pg --activation-policy=NEVER` | 0 |
| **Delete** Redis (cache, recreatable) | `gcloud redis instances delete precision-genomics-redis --region=us-central1` | 0 |
| **Delete** VPC connector (recreatable) | `gcloud compute networks vpc-access connectors delete precision-genomics-vpc --region=us-central1` | 0 |

Kept, untouched: all 3 Cloud Run services (dormant), all 4 GCS buckets (incl. genomics data/models),
Artifact Registry images, both secrets, the `precision-genomics-vpc` network itself, `infra-ts/` IaC.

## 5. Verify-effect (state re-probed — NOT trusting delete exit codes)
- Cloud SQL: `state=STOPPED`, `activationPolicy=NEVER` ✓ (data retained, compute billing halted).
- Redis: `gcloud redis instances list` → **Listed 0 items** ✓.
- VPC connector: `gcloud …connectors list` → **Listed 0 items** ✓.
- Cloud Run: 3 services still present ✓. Buckets: 4 present ✓. API image repo intact ✓.
- **Estimated recurring cut: ~$145–195/mo → a few $/mo** (stopped-SQL storage + retained buckets/images).
- **BILLING NOT YET PROVEN AT SKU LEVEL:** resource state is verified now, but "no longer billed" lags
  in the billing console. **Confirm the SQL/Redis/connector SKUs drop to ~zero in the billing console
  in 24–48h** — that is the real verify-effect on cost, still outstanding.

## 6. Reversibility / redeploy
- **Cloud SQL:** restart with `gcloud sql instances patch precision-genomics-pg --activation-policy=ALWAYS`. Data intact.
- **Redis + VPC connector:** deleted, but recreatable from `infra-ts/` (Pulumi). NOTE the known DRIFT —
  running services (`api/mcp-sse/worker`) ≠ the `infra-ts` stack (`web/intent/ml/mcp`); a Pulumi
  redeploy may not reproduce this exact platform. Redeploy would need the drift reconciled first.
- Cloud Run services are kept but will fail to reach SQL/Redis on cold start (connector gone, DB
  stopped) until reversed — they are dormant, not functional.

## 7. Demo honesty check
`passed-vs-true-demo` never claimed anything "live" about GCP (it is replay-with-provenance, and
v1 shipped no live-GCP CTA). So **no demo change is required** by this decommission. If a "go see
the live system" link is ever added, it must NOT point at this now-dormant platform.
