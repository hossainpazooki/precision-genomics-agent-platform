"""Vertex AI Custom Training Job wrapper."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def submit_training_job(
    dataset_uri: str,
    target: str,
    config: dict | None = None,
    project: str | None = None,
    location: str = "us-central1",
    staging_bucket: str | None = None,
    display_name: str = "precision-genomics-training",
) -> str:
    """Submit a custom training job to Vertex AI.

    Parameters
    ----------
    dataset_uri : str
        GCS URI of the training dataset (e.g., gs://bucket/data/train_pro.tsv).
    target : str
        Target column name (e.g., 'msi', 'gender').
    config : dict, optional
        Pipeline configuration overrides.
    project : str, optional
        GCP project ID.
    location : str
        GCP region.
    staging_bucket : str, optional
        GCS bucket for staging artifacts.
    display_name : str
        Display name for the training job.

    Returns
    -------
    str
        The Vertex AI job resource name.
    """
    from google.cloud import aiplatform

    aiplatform.init(project=project, location=location, staging_bucket=staging_bucket)

    worker_pool_specs = [
        {
            "machine_spec": {
                "machine_type": "n1-standard-4",
            },
            "replica_count": 1,
            "container_spec": {
                "image_uri": "us-docker.pkg.dev/vertex-ai/training/sklearn-cpu.1-3:latest",
                "command": ["python", "-m", "scripts.vertex_train_entrypoint"],
                "args": [
                    f"--dataset-uri={dataset_uri}",
                    f"--target={target}",
                    f"--config={_serialize_config(config or {})}",
                ],
            },
        }
    ]

    job = aiplatform.CustomJob(
        display_name=display_name,
        worker_pool_specs=worker_pool_specs,
    )

    job.run(sync=False)
    logger.info("Submitted Vertex AI training job: %s", job.resource_name)
    return job.resource_name


def submit_gpu_training_job(
    dataset_uri: str,
    target: str,
    config: dict | None = None,
    accelerator_type: str = "NVIDIA_TESLA_A100",
    accelerator_count: int = 1,
    machine_type: str = "a2-highgpu-1g",
    container_uri: str | None = None,
    project: str | None = None,
    location: str = "us-central1",
    staging_bucket: str | None = None,
    display_name: str = "precision-genomics-gpu-training",
) -> str:
    """Submit a GPU-accelerated training job to Vertex AI.

    Parameters
    ----------
    dataset_uri : str
        GCS URI of the training dataset.
    target : str
        Target column name.
    config : dict, optional
        Pipeline configuration overrides.
    accelerator_type : str
        GPU accelerator type (default: NVIDIA_TESLA_A100).
    accelerator_count : int
        Number of GPUs per worker (default: 1).
    machine_type : str
        Machine type (default: a2-highgpu-1g).
    container_uri : str, optional
        Custom container image URI.
    project : str, optional
        GCP project ID.
    location : str
        GCP region.
    staging_bucket : str, optional
        GCS bucket for staging artifacts.
    display_name : str
        Display name for the training job.

    Returns
    -------
    str
        The Vertex AI job resource name.
    """
    from google.cloud import aiplatform

    aiplatform.init(project=project, location=location, staging_bucket=staging_bucket)

    if container_uri is None:
        container_uri = "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-1:latest"

    worker_pool_specs = [
        {
            "machine_spec": {
                "machine_type": machine_type,
                "accelerator_type": accelerator_type,
                "accelerator_count": accelerator_count,
            },
            "replica_count": 1,
            "container_spec": {
                "image_uri": container_uri,
                "command": ["python", "-m", "scripts.slm_train_entrypoint"],
                "args": [
                    f"--dataset-uri={dataset_uri}",
                    f"--mode={(config or {}).get('mode', 'qlora')}",
                ],
            },
        }
    ]

    job = aiplatform.CustomJob(
        display_name=display_name,
        worker_pool_specs=worker_pool_specs,
    )

    job.run(sync=False)
    logger.info("Submitted GPU training job: %s", job.resource_name)
    return job.resource_name


def _serialize_config(config: dict) -> str:
    """Serialize config dict to a JSON string for CLI args."""
    import json

    return json.dumps(config)
