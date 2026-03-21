"""Automation API: ML-triggered infrastructure updates.

Demonstrates Pulumi's Automation API — infrastructure as a callable library.
After a model retraining completes, this script programmatically updates
Cloud Run service images and scales worker instances, without requiring
the Pulumi CLI.

Usage:
    # Called from the ML pipeline after retraining
    python -m infra.automation.deploy_on_model_retrain \\
        --stack prod \\
        --image-tag abc123def

    # Or called programmatically from Python
    from infra.automation.deploy_on_model_retrain import deploy_model_update
    await deploy_model_update(stack_name="prod", image_tag="abc123def")
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from pulumi import automation as auto


INFRA_DIR = str(Path(__file__).resolve().parent.parent)
PROJECT_NAME = "precision-genomics"


async def deploy_model_update(
    stack_name: str,
    image_tag: str,
    worker_max_instances: int | None = None,
) -> dict[str, str]:
    """Programmatically update infrastructure after model retraining.

    Args:
        stack_name: Pulumi stack (dev/staging/prod).
        image_tag: Docker image tag for the newly trained model container.
        worker_max_instances: Optionally scale up workers during retraining.

    Returns:
        Dict of Pulumi stack outputs (service URLs, etc.).
    """
    stack = await auto.create_or_select_stack(
        stack_name=stack_name,
        project_name=PROJECT_NAME,
        work_dir=INFRA_DIR,
    )

    print(f"Updating stack '{stack_name}' with image tag '{image_tag}'...")

    # Set the image tag override via stack config
    await stack.set_config(
        "precision-genomics:image_tag",
        auto.ConfigValue(value=image_tag),
    )

    # Optionally scale up workers for retraining workloads
    if worker_max_instances is not None:
        await stack.set_config(
            "precision-genomics:worker_max_instances",
            auto.ConfigValue(value=str(worker_max_instances)),
        )

    # Install Python dependencies for the Pulumi program
    await stack.workspace.install_plugin("gcp", "v7.0.0")

    # Run pulumi up
    up_result = await stack.up(on_output=print)

    outputs = {k: v.value for k, v in up_result.outputs.items()}

    print(f"\nDeployment complete. API URL: {outputs.get('api_url')}")
    print(f"Worker URL: {outputs.get('activity_worker_url')}")

    return outputs


async def destroy_training_resources(stack_name: str) -> None:
    """Tear down ephemeral GPU training resources after retraining completes.

    This is called after the Vertex AI training job finishes to clean up
    any temporary infrastructure (e.g. scaled-up worker instances).
    """
    stack = await auto.create_or_select_stack(
        stack_name=stack_name,
        project_name=PROJECT_NAME,
        work_dir=INFRA_DIR,
    )

    # Reset worker scaling to defaults
    await stack.remove_config("precision-genomics:worker_max_instances")

    print(f"Resetting worker scaling for stack '{stack_name}'...")
    await stack.up(on_output=print)
    print("Worker scaling reset to defaults.")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy infrastructure updates after model retraining"
    )
    parser.add_argument(
        "--stack", required=True, help="Pulumi stack name (dev/staging/prod)"
    )
    parser.add_argument(
        "--image-tag", required=True, help="Docker image tag for the new model"
    )
    parser.add_argument(
        "--worker-scale", type=int, default=None,
        help="Temporarily scale worker max instances",
    )
    args = parser.parse_args()

    asyncio.run(
        deploy_model_update(
            stack_name=args.stack,
            image_tag=args.image_tag,
            worker_max_instances=args.worker_scale,
        )
    )


if __name__ == "__main__":
    main()
