"""Automation API: intent-triggered infrastructure scaling.

Follows the same pattern as deploy_on_model_retrain.py — uses Pulumi
Automation API to programmatically adjust infrastructure for intent
execution, then resets when the intent completes.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from pulumi import automation as auto

INFRA_DIR = str(Path(__file__).resolve().parent.parent)
PROJECT_NAME = "precision-genomics"


async def scale_for_intent(
    stack_name: str,
    intent_type: str,
    worker_max_instances: int | None = None,
) -> dict[str, str]:
    """Scale infrastructure for an intent's execution needs.

    Args:
        stack_name: Pulumi stack (dev/staging/prod).
        intent_type: analysis | training | validation.
        worker_max_instances: Override max worker instances.

    Returns:
        Dict of Pulumi stack outputs.
    """
    stack = await auto.create_or_select_stack(
        stack_name=stack_name,
        project_name=PROJECT_NAME,
        work_dir=INFRA_DIR,
    )

    print(f"Scaling stack '{stack_name}' for {intent_type} intent...")

    if worker_max_instances is not None:
        await stack.set_config(
            "precision-genomics:worker_max_instances",
            auto.ConfigValue(value=str(worker_max_instances)),
        )

    # Tag the stack with intent metadata for audit.
    await stack.set_config(
        "precision-genomics:active_intent_type",
        auto.ConfigValue(value=intent_type),
    )

    up_result = await stack.up(on_output=print)
    outputs = {k: v.value for k, v in up_result.outputs.items()}

    print(f"Scaling complete for {intent_type} intent.")
    return outputs


async def teardown_intent_resources(stack_name: str) -> None:
    """Reset infrastructure after an intent completes.

    Removes intent-specific config overrides and applies defaults.
    """
    stack = await auto.create_or_select_stack(
        stack_name=stack_name,
        project_name=PROJECT_NAME,
        work_dir=INFRA_DIR,
    )

    print(f"Resetting intent resources for stack '{stack_name}'...")

    await stack.remove_config("precision-genomics:worker_max_instances")
    await stack.remove_config("precision-genomics:active_intent_type")

    await stack.up(on_output=print)
    print("Intent resources reset to defaults.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scale infra for intent execution")
    parser.add_argument("--stack", required=True)
    parser.add_argument("--intent-type", required=True, choices=["analysis", "training", "validation"])
    parser.add_argument("--worker-max", type=int, default=None)
    parser.add_argument("--teardown", action="store_true")
    args = parser.parse_args()

    if args.teardown:
        asyncio.run(teardown_intent_resources(args.stack))
    else:
        asyncio.run(
            scale_for_intent(
                stack_name=args.stack,
                intent_type=args.intent_type,
                worker_max_instances=args.worker_max,
            )
        )
