"""GPU training activities."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def train_expression_encoder_activity(config: dict) -> dict:
    """Submit expression encoder training job to Vertex AI."""
    from google.cloud import aiplatform

    from training.gpu_configs import GPU_TRAINING_CONFIG

    gpu_config = GPU_TRAINING_CONFIG["expression_encoder"]

    project = config.get("project")
    location = config.get("location", "us-central1")
    staging_bucket = config.get("staging_bucket")

    aiplatform.init(project=project, location=location, staging_bucket=staging_bucket)

    import json

    training_config = {
        k: v
        for k, v in config.items()
        if k not in ("project", "location", "staging_bucket", "image_uri")
    }

    n_gpus = config.get("n_gpus", gpu_config["accelerator_count"])

    worker_pool_specs = [
        {
            "machine_spec": {
                "machine_type": gpu_config["machine_type"],
                "accelerator_type": gpu_config["accelerator_type"],
                "accelerator_count": n_gpus,
            },
            "replica_count": 1,
            "container_spec": {
                "image_uri": config.get(
                    "image_uri",
                    "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-2:latest",
                ),
                "command": ["python", "-m", "scripts.encoder_train_entrypoint"],
                "args": [
                    f"--dataset-uri={config['dataset_uri']}",
                    f"--config={json.dumps(training_config)}",
                    f"--num-gpus={n_gpus}",
                ],
            },
        }
    ]

    job = aiplatform.CustomJob(
        display_name=config.get("display_name", "expression-encoder-training"),
        worker_pool_specs=worker_pool_specs,
    )

    job.run(sync=False)
    logger.info("Submitted encoder training job: %s", job.resource_name)

    return {
        "job_name": job.resource_name,
        "status": "submitted",
        "gpu_config": gpu_config,
    }


async def finetune_slm_activity(config: dict) -> dict:
    """Submit SLM fine-tuning job to Vertex AI."""
    from google.cloud import aiplatform

    from training.gpu_configs import GPU_TRAINING_CONFIG

    gpu_config = GPU_TRAINING_CONFIG["slm_finetuning"]

    project = config.get("project")
    location = config.get("location", "us-central1")
    staging_bucket = config.get("staging_bucket")

    aiplatform.init(project=project, location=location, staging_bucket=staging_bucket)

    import json

    training_config = {
        k: v
        for k, v in config.items()
        if k not in ("project", "location", "staging_bucket", "image_uri")
    }

    worker_pool_specs = [
        {
            "machine_spec": {
                "machine_type": gpu_config["machine_type"],
                "accelerator_type": gpu_config["accelerator_type"],
                "accelerator_count": gpu_config["accelerator_count"],
            },
            "replica_count": 1,
            "container_spec": {
                "image_uri": config.get(
                    "image_uri",
                    "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-2:latest",
                ),
                "command": ["python", "-m", "scripts.slm_train_entrypoint"],
                "args": [
                    f"--config={json.dumps(training_config)}",
                ],
            },
        }
    ]

    job = aiplatform.CustomJob(
        display_name=config.get("display_name", "slm-finetuning"),
        worker_pool_specs=worker_pool_specs,
    )

    job.run(sync=False)
    logger.info("Submitted SLM fine-tuning job: %s", job.resource_name)

    return {
        "job_name": job.resource_name,
        "status": "submitted",
        "gpu_config": gpu_config,
    }


async def run_cuml_pipeline_activity(config: dict) -> dict:
    """Run GPU-accelerated classification pipeline."""
    from google.cloud import aiplatform

    from training.gpu_configs import GPU_TRAINING_CONFIG

    gpu_config = GPU_TRAINING_CONFIG["cuml_benchmark"]

    project = config.get("project")
    location = config.get("location", "us-central1")
    staging_bucket = config.get("staging_bucket")

    aiplatform.init(project=project, location=location, staging_bucket=staging_bucket)

    import json

    training_config = {
        k: v
        for k, v in config.items()
        if k not in ("project", "location", "staging_bucket", "image_uri")
    }

    worker_pool_specs = [
        {
            "machine_spec": {
                "machine_type": gpu_config["machine_type"],
                "accelerator_type": gpu_config["accelerator_type"],
                "accelerator_count": gpu_config["accelerator_count"],
            },
            "replica_count": 1,
            "container_spec": {
                "image_uri": config.get(
                    "image_uri",
                    "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-2:latest",
                ),
                "command": ["python", "-m", "scripts.vertex_train_entrypoint"],
                "args": [
                    f"--dataset-uri={config['dataset_uri']}",
                    f"--target={config.get('target', 'msi')}",
                    f"--config={json.dumps(training_config)}",
                ],
            },
        }
    ]

    job = aiplatform.CustomJob(
        display_name=config.get("display_name", "cuml-classification"),
        worker_pool_specs=worker_pool_specs,
    )

    job.run(sync=False)
    logger.info("Submitted cuML pipeline job: %s", job.resource_name)

    return {
        "job_name": job.resource_name,
        "status": "submitted",
        "gpu_config": gpu_config,
    }
