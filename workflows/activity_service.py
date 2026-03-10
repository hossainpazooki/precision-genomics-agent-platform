"""FastAPI app exposing workflow activities as HTTP endpoints.

Deployed as a dedicated Cloud Run service (activity-worker) that handles
long-running ML work separately from the user-facing API.
"""

from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

logger = logging.getLogger(__name__)

# Registry mapping activity names to their async functions
_ACTIVITY_REGISTRY: dict[str, tuple] = {}


def _register_activities() -> None:
    """Register all activity functions with their argument specs."""
    from workflows.activities.claude_activities import (
        compile_report_activity,
        generate_interpretation_activity,
    )
    from workflows.activities.data_activities import (
        load_and_validate_data_activity,
        load_clinical_data_activity,
        load_molecular_data_activity,
        run_classification_qc_activity,
    )
    from workflows.activities.dspy_activities import (
        compare_and_deploy_activity,
        compile_dspy_modules_activity,
        generate_synthetic_cohort_activity,
        run_pipeline_with_prompts_activity,
    )
    from workflows.activities.ml_activities import (
        cross_validate_flags_activity,
        impute_data_activity,
        integrate_and_filter_activity,
        log_experiment_metrics_activity,
        quarantine_samples_activity,
        run_cosmo_pipeline_activity,
        run_distance_matrix_activity,
        select_features_activity,
        train_and_evaluate_activity,
        upload_model_to_gcs_activity,
    )

    registry = {
        # Data activities
        "load_and_validate_data": load_and_validate_data_activity,
        "load_clinical_data": load_clinical_data_activity,
        "load_molecular_data": load_molecular_data_activity,
        "run_classification_qc": run_classification_qc_activity,
        # ML activities
        "impute_data": impute_data_activity,
        "select_features": select_features_activity,
        "integrate_and_filter": integrate_and_filter_activity,
        "train_and_evaluate": train_and_evaluate_activity,
        "run_distance_matrix": run_distance_matrix_activity,
        "run_cosmo_pipeline": run_cosmo_pipeline_activity,
        "cross_validate_flags": cross_validate_flags_activity,
        "quarantine_samples": quarantine_samples_activity,
        "upload_model_to_gcs": upload_model_to_gcs_activity,
        "log_experiment_metrics": log_experiment_metrics_activity,
        # Claude activities
        "generate_interpretation": generate_interpretation_activity,
        "compile_report": compile_report_activity,
        # DSPy activities
        "generate_synthetic_cohort": generate_synthetic_cohort_activity,
        "run_pipeline_with_prompts": run_pipeline_with_prompts_activity,
        "compile_dspy_modules": compile_dspy_modules_activity,
        "compare_and_deploy": compare_and_deploy_activity,
    }
    _ACTIVITY_REGISTRY.update(registry)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _register_activities()
    yield


app = FastAPI(title="Precision Genomics Activity Worker", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "activities": list(_ACTIVITY_REGISTRY.keys())}


@app.post("/activities/{activity_name}")
async def run_activity(activity_name: str, body: dict) -> dict:
    """Execute an activity function by name.

    The request body should contain:
    - ``args``: positional arguments list
    - ``kwargs``: keyword arguments dict
    - ``workflow_id``: (optional) for progress tracking
    """
    if activity_name not in _ACTIVITY_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown activity: {activity_name}. Available: {sorted(_ACTIVITY_REGISTRY.keys())}",
        )

    fn = _ACTIVITY_REGISTRY[activity_name]
    args = body.get("args", [])
    kwargs = body.get("kwargs", {})
    workflow_id = body.get("workflow_id")

    # Update progress if workflow_id provided
    if workflow_id:
        try:
            from workflows.progress import update_progress

            await update_progress(workflow_id, current_phase=activity_name, status="running")
        except Exception:
            logger.debug("Could not update progress for %s", workflow_id)

    try:
        result = await fn(*args, **kwargs)

        if workflow_id:
            try:
                from workflows.progress import update_progress

                await update_progress(workflow_id, phase_completed=activity_name)
            except Exception:
                logger.debug("Could not update progress for %s", workflow_id)

        return {"status": "ok", "result": result}

    except Exception as exc:
        logger.error("Activity %s failed: %s", activity_name, traceback.format_exc())

        if workflow_id:
            try:
                from workflows.progress import update_progress

                await update_progress(workflow_id, status="failed", error=str(exc))
            except Exception:
                pass

        raise HTTPException(status_code=500, detail=str(exc)) from exc
