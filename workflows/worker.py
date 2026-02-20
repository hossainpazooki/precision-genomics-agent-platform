"""Temporal worker process for genomics workflows."""

from __future__ import annotations

import asyncio
import logging

try:
    from temporalio.client import Client
    from temporalio.worker import Worker

    HAS_TEMPORAL = True
except ImportError:
    HAS_TEMPORAL = False

from workflows.config import WorkflowConfig

logger = logging.getLogger(__name__)


if HAS_TEMPORAL:
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
    from workflows.activities.ml_activities import (
        cross_validate_flags_activity,
        impute_data_activity,
        integrate_and_filter_activity,
        quarantine_samples_activity,
        run_distance_matrix_activity,
        select_features_activity,
        train_and_evaluate_activity,
    )
    from workflows.biomarker_discovery import BiomarkerDiscoveryWorkflow
    from workflows.sample_qc import SampleQCWorkflow

    WORKFLOWS = [BiomarkerDiscoveryWorkflow, SampleQCWorkflow]

    ACTIVITIES = [
        # Data activities
        load_and_validate_data_activity,
        load_clinical_data_activity,
        load_molecular_data_activity,
        run_classification_qc_activity,
        # ML activities
        impute_data_activity,
        select_features_activity,
        integrate_and_filter_activity,
        train_and_evaluate_activity,
        run_distance_matrix_activity,
        cross_validate_flags_activity,
        quarantine_samples_activity,
        # Claude activities
        generate_interpretation_activity,
        compile_report_activity,
    ]


async def create_client() -> Client:
    """Create a Temporal client connection."""
    if not HAS_TEMPORAL:
        raise RuntimeError("temporalio is not installed")

    config = WorkflowConfig()
    return await Client.connect(
        config.host,
        namespace=config.namespace,
    )


async def create_worker(client: Client) -> Worker:
    """Create a Temporal worker with all registered workflows and activities."""
    if not HAS_TEMPORAL:
        raise RuntimeError("temporalio is not installed")

    config = WorkflowConfig()
    return Worker(
        client,
        task_queue=config.task_queue,
        workflows=WORKFLOWS,
        activities=ACTIVITIES,
    )


async def run_worker() -> None:
    """Connect to Temporal and run the worker until interrupted."""
    logger.info("Starting Temporal worker...")
    client = await create_client()
    worker = await create_worker(client)
    logger.info("Worker connected, processing tasks on queue: %s", WorkflowConfig().task_queue)
    await worker.run()


def main() -> None:
    """Entry point for the worker process."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
