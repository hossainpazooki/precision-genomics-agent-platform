# Intent Lifecycle Workflow

The intent lifecycle layer sits between the agent/workflow layer and the Pulumi infrastructure layer, formalizing agent goals as infrastructure-level concerns with the **observe-decide-act-verify** loop from intent-based networking.

## Overview

```mermaid
flowchart TB
    subgraph Origin["Intent Origin"]
        MCP["MCP Tool\n(express_intent)"]
        API["API Route"]
        Skill["Agent Skill"]
    end

    subgraph Lifecycle["Intent Controller"]
        D["DECLARED"]
        R["RESOLVING"]
        B["BLOCKED"]
        A["ACTIVE"]
        V["VERIFYING"]
        AC["ACHIEVED"]
        F["FAILED"]
    end

    subgraph Infra["Infrastructure Layer"]
        PR["Pulumi\nAutomation API"]
        GCS["GCS Data\nStaging"]
        WS["Worker\nScaling"]
        GPU["Vertex AI\nGPU Provisioning"]
    end

    subgraph Execution["Execution Layer"]
        WF["Workflow Engine\n(LocalWorkflowRunner)"]
        COSMO["COSMO Pipeline\n4 Stages"]
        VTX["Vertex AI\nTraining Job"]
    end

    subgraph Assurance["Assurance Loop"]
        BIO["Biological Validity\n≥60%"]
        REP["Reproducibility\n≥85%"]
        HAL["Hallucination Detection\n≥90%"]
    end

    MCP & API & Skill --> D
    D --> R
    R --> PR
    PR --> WS & GCS & GPU
    R -->|"infra ready"| A
    R -->|"infra failed"| B
    B -->|"retry"| R
    A --> WF
    WF --> COSMO & VTX
    A -->|"workflows done"| V
    A -->|"workflow failed"| F
    V --> BIO & REP & HAL
    V -->|"all pass"| AC
    V -->|"any fail"| F
```

## State Machine

The intent lifecycle uses an explicit state machine with the following states and transitions:

```mermaid
stateDiagram-v2
    [*] --> declared
    declared --> resolving: Controller picks up
    resolving --> active: Infra provisioned
    resolving --> blocked: Infra failed / policy violation
    blocked --> resolving: Retry
    active --> verifying: All workflows complete
    active --> failed: Workflow failed (non-retryable)
    verifying --> achieved: All evals pass
    verifying --> failed: Eval criteria not met
    declared --> cancelled: Explicit cancel
    resolving --> cancelled: Explicit cancel
    blocked --> cancelled: Explicit cancel
    active --> cancelled: Explicit cancel
    verifying --> cancelled: Explicit cancel
    achieved --> [*]
    failed --> [*]
    cancelled --> [*]
```

| State | Description | Phase |
|-------|-------------|-------|
| `declared` | Intent expressed, not yet acted on | — |
| `resolving` | Checking/provisioning infrastructure via Pulumi | **Decide** |
| `blocked` | Infra resolution failed or prerequisite unmet | **Decide** (retry) |
| `active` | Child workflows executing | **Act** |
| `verifying` | Eval assurance loop running | **Verify** |
| `achieved` | All success criteria met (terminal) | — |
| `failed` | Criteria not met or unrecoverable error (terminal) | — |
| `cancelled` | Explicitly cancelled (terminal) | — |

## Three Intent Types

### AnalysisIntent

Biomarker discovery, sample QC, or cross-omics matching on a dataset.

```mermaid
sequenceDiagram
    participant Agent
    participant Controller
    participant Pulumi as Pulumi Automation API
    participant Worker as Workflow Engine
    participant Eval as Assurance Loop

    Agent->>Controller: express_intent(type="analysis", target="msi")
    Controller->>Controller: DECLARED → RESOLVING

    rect rgb(240, 248, 255)
        Note over Controller,Pulumi: Infrastructure Resolution
        Controller->>Pulumi: scale_for_intent(worker_max=5)
        Pulumi-->>Controller: stack outputs (worker_url)
        Controller->>Controller: verify GCS data staged
    end

    Controller->>Controller: RESOLVING → ACTIVE

    rect rgb(240, 255, 240)
        Note over Controller,Worker: Workflow Execution
        Controller->>Worker: run_biomarker_discovery(target, modalities)
        Worker->>Worker: Impute → Match → Predict → Correct
        Worker-->>Controller: workflow completed
    end

    Controller->>Controller: ACTIVE → VERIFYING

    rect rgb(255, 248, 240)
        Note over Controller,Eval: Assurance Loop
        Controller->>Eval: biological_validity(genes, threshold=0.60)
        Eval-->>Controller: score=0.75, PASS
        Controller->>Eval: reproducibility(pipeline, threshold=0.85)
        Eval-->>Controller: score=0.90, PASS
    end

    Controller->>Controller: VERIFYING → ACHIEVED
    Controller-->>Agent: intent achieved
```

**Infrastructure needs:** Worker service scaled, GCS data staged.
**Success criteria:** Biological validity ≥ 60% pathway coverage, reproducibility ≥ 85% Jaccard.
**Validation gate:** Cannot proceed past COSMO Stage 2 without a passing `ValidationIntent`.

### TrainingIntent

Fine-tune BioMistral, retrain expression encoder, or run GPU-accelerated classification.

```mermaid
sequenceDiagram
    participant Agent
    participant Controller
    participant Pulumi as Pulumi Automation API
    participant Vertex as Vertex AI
    participant Deploy as deploy_on_model_retrain

    Agent->>Controller: express_intent(type="training", model_type="slm")
    Controller->>Controller: DECLARED → RESOLVING

    rect rgb(240, 248, 255)
        Note over Controller,Pulumi: GPU Provisioning
        Controller->>Controller: check GPU quota (≤4 GPUs)
        Controller->>Vertex: finetune_slm_activity(config)
        Vertex-->>Controller: job provisioned
    end

    Controller->>Controller: RESOLVING → ACTIVE

    rect rgb(240, 255, 240)
        Note over Controller,Vertex: Training Execution
        Vertex->>Vertex: QLoRA fine-tuning on A100
        Vertex-->>Controller: job completed
    end

    Controller->>Controller: ACTIVE → VERIFYING → ACHIEVED
    Note over Controller: No eval criteria for training

    rect rgb(255, 240, 245)
        Note over Controller,Deploy: Post-Training Deploy Chain
        Controller->>Deploy: deploy_model_update(image_tag)
        Deploy->>Pulumi: stack.set_config(image_tag) → stack.up()
        Deploy-->>Controller: deployment complete
    end
```

**Infrastructure needs:** Vertex AI training job provisioned, GPU quota validated.
**Success criteria:** Job completion (no eval criteria).
**Post-success:** Automatically chains to `deploy_on_model_retrain.deploy_model_update()`.
**Guardrail:** Max 4 GPUs per stack (enforced by CrossGuard policy).

### ValidationIntent

Cross-omics concordance verification — acts as a gate for AnalysisIntent.

```mermaid
sequenceDiagram
    participant Agent
    participant Controller
    participant Worker as Workflow Engine
    participant Eval as Assurance Loop

    Agent->>Controller: express_intent(type="validation")
    Controller->>Controller: DECLARED → RESOLVING → ACTIVE
    Note over Controller: Minimal infra (no provisioning needed)

    Controller->>Worker: run_sample_qc(dataset)
    Worker->>Worker: Dual-path validation (Stage 4)
    Worker-->>Controller: completed

    Controller->>Controller: ACTIVE → VERIFYING

    Controller->>Eval: hallucination_detection(threshold=0.90)
    Eval-->>Controller: score=0.95, PASS

    Controller->>Controller: VERIFYING → ACHIEVED
    Note over Controller: AnalysisIntent can now proceed past Stage 2
```

**Infrastructure needs:** None (minimal).
**Success criteria:** Hallucination detection ≥ 90% citation verification.
**Purpose:** No AnalysisIntent proceeds past COSMO Stage 2 without a passing ValidationIntent.

## Data Model

Two PostgreSQL tables persist intent state (same SQLModel pattern as `workflows/progress.py`):

```mermaid
erDiagram
    intents {
        int id PK
        string intent_id UK "analysis-a1b2c3d4"
        string intent_type "analysis | training | validation"
        string status "declared → achieved"
        json params "what was requested"
        json infra_state "resolution results"
        json workflow_ids "child workflow IDs"
        json eval_results "assurance outcomes"
        datetime created_at
        datetime resolved_at
        datetime activated_at
        datetime completed_at
        string error
        string requested_by "agent | api | mcp"
    }

    intent_events {
        int id PK
        string intent_id FK
        string event_type "state_change | workflow_started | eval_completed"
        string from_status
        string to_status
        json payload
        datetime timestamp
    }

    workflow_executions {
        int id PK
        string workflow_id UK
        string workflow_type
        string status
        string current_phase
        json phases_completed
        json result
    }

    intents ||--o{ intent_events : "audit trail"
    intents ||--o{ workflow_executions : "child workflows"
```

## Controller Architecture

The controller is **not** a long-running daemon. It is called per-intent and is idempotent — safe to call repeatedly, advancing the intent through whatever state transition is currently possible.

```mermaid
flowchart LR
    subgraph Controller["IntentController.process()"]
        direction TB
        OBS["Observe\n(load intent state)"]
        DEC["Decide\n(resolve infra)"]
        ACT["Act\n(trigger workflows)"]
        VER["Verify\n(run evals)"]
        OBS --> DEC --> ACT --> VER
    end

    subgraph Dependencies["Injected Dependencies"]
        IR["InfrastructureResolver"]
        AL["AssuranceLoop"]
    end

    IR --> DEC
    AL --> VER
```

```python
# Idempotent — call repeatedly to advance the intent
controller = get_controller()
result = await controller.process(intent_id)
# Returns the intent dict with updated status
```

## Infrastructure Resolution

The `InfrastructureResolver` maps intent requirements to Pulumi Automation API operations, wrapping existing scripts in `infra/automation/`:

```mermaid
flowchart LR
    subgraph Requirements["Intent Requirements"]
        WS[worker_scaled]
        GCS[gcs_data_staged]
        VTX[vertex_ai_job]
        GPU[gpu_allocated]
    end

    subgraph Handlers["Resolution Handlers"]
        H1["scale_for_intent()\nPulumi stack.up()"]
        H2["Check GCS bucket\nfor dataset files"]
        H3["finetune_slm_activity()\nor train_encoder_activity()"]
        H4["Validate against\nmax_gpu_count"]
    end

    subgraph Existing["Existing Automation Scripts"]
        DM["deploy_on_model_retrain.py"]
        EE["ephemeral_env.py"]
        II["intent_infra.py (new)"]
    end

    WS --> H1 --> II
    GCS --> H2
    VTX --> H3
    GPU --> H4

    II -.->|"same pattern as"| DM
    II -.->|"same pattern as"| EE
```

## Assurance Loop

The `AssuranceLoop` wraps the existing `evals/` framework and wires eval results into intent state transitions:

| Eval | Class | Threshold | Used By |
|------|-------|-----------|---------|
| Biological Validity | `BiologicalValidityEval` | ≥ 60% pathway coverage | AnalysisIntent |
| Reproducibility | `ReproducibilityEval` | ≥ 85% pairwise Jaccard | AnalysisIntent |
| Hallucination Detection | `HallucinationDetectionEval` | ≥ 90% citation verification | ValidationIntent |

All evals return `EvalResult(name, passed, score, threshold, details)`. If `all_passed()` returns `True`, the intent transitions to `achieved`. Otherwise, `failed`.

## MCP Integration

Two new tools are registered in the MCP server (11 total):

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `express_intent` | `{intent_type, params}` | `{intent_id, status, message}` | Create and begin processing an intent |
| `get_intent_status` | `{intent_id}` | `{status, workflow_ids, eval_results, ...}` | Poll intent progress and results |

Example agent interaction:

```
Agent: Call express_intent with intent_type="analysis", params={"target": "msi", "dataset": "train"}
→ Returns: intent_id="analysis-a1b2c3d4", status="resolving"

Agent: Call get_intent_status with intent_id="analysis-a1b2c3d4"
→ Returns: status="verifying", eval_results={"biological_validity": {"score": 0.75, "passed": true}}

Agent: Call get_intent_status with intent_id="analysis-a1b2c3d4"
→ Returns: status="achieved"
```

## CrossGuard Policy Extensions

Two new policies extend the existing 8 compliance guardrails:

| Policy | Level | Rule |
|--------|-------|------|
| `training-gpu-limit` | Mandatory | Training intents cannot provision > 4 GPUs per stack |
| `intent-resource-labels` | Advisory | Intent-provisioned resources should carry `intent-id` and `intent-type` labels |

## File Layout

```
intents/                              # Intent lifecycle layer
├── __init__.py                       # Exports
├── schemas.py                        # IntentStatus enum, valid transitions
├── types.py                          # AnalysisIntentSpec, TrainingIntentSpec, ValidationIntentSpec
├── models.py                         # SQLModel tables + persistence functions
├── controller.py                     # IntentController (observe-decide-act-verify)
├── infra_resolver.py                 # Maps intent needs → Pulumi Automation API
├── assurance.py                      # Wraps evals/ for intent success/failure
├── service.py                        # create_intent(), get_intent(), get_controller()

infra/automation/intent_infra.py      # Pulumi Automation API for intent scaling
infra/policies/genomics_policies.py   # +2 intent-specific CrossGuard policies

mcp_server/schemas/intents.py         # Pydantic I/O schemas for intent tools
mcp_server/tools/intent_manager.py    # express_intent tool
mcp_server/tools/intent_status.py     # get_intent_status tool
```

## Design Principles

1. **Intents are not workflows.** A workflow is an execution plan. An intent is a goal with success criteria. One intent may trigger multiple workflows.
2. **Eval metrics are the assurance loop.** Quantitative thresholds from `evals/` drive `active → achieved` vs `active → failed`.
3. **Pulumi Automation API, not raw gcloud.** Infrastructure changes go through the same stack operations as `deploy_on_model_retrain.py`.
4. **Controller is idempotent.** Safe to call `process()` repeatedly — advances through whatever transition is possible.
5. **Core ML untouched.** `core/` doesn't know about intents. The intent layer orchestrates around it.

## Future: Go Migration

The intent controller is a natural candidate for migration to Go:
- Go's concurrency model (goroutines, channels) fits the observe-decide-act-verify loop
- Single-binary deployment simplifies the controller as a long-running service
- Pulumi has first-class Go Automation API support
- The controller's interface is simple enough to port without changing the data model

Ship in Python first alongside the existing stack. Migrate to Go when the lifecycle stabilizes.
