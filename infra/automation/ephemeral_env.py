"""Automation API: Ephemeral PR preview environments.

Demonstrates programmatic stack lifecycle management — creates a full
isolated environment (Cloud Run + Cloud SQL + Redis) for each pull request,
posts the preview URL as a PR comment, and tears it down on merge/close.

Usage:
    # Create a preview environment for PR #42
    python -m infra.automation.ephemeral_env create --pr 42

    # Destroy the preview environment
    python -m infra.automation.ephemeral_env destroy --pr 42

Integration:
    Called from GitHub Actions on PR open/close events.
    See .github/workflows/deploy-pulumi.yml for the preview job.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from pulumi import automation as auto


INFRA_DIR = str(Path(__file__).resolve().parent.parent)
PROJECT_NAME = "precision-genomics"


def _stack_name(pr_number: int) -> str:
    """Generate a deterministic stack name for a PR."""
    return f"pr-{pr_number}"


async def create_preview(pr_number: int) -> dict[str, str]:
    """Spin up a complete isolated environment for a PR.

    Creates a new Pulumi stack with lightweight resource configs
    (smaller DB tier, fewer instances) to minimize cost.

    Args:
        pr_number: GitHub PR number.

    Returns:
        Dict with preview URLs and resource identifiers.
    """
    stack_name = _stack_name(pr_number)

    stack = await auto.create_or_select_stack(
        stack_name=stack_name,
        project_name=PROJECT_NAME,
        work_dir=INFRA_DIR,
    )

    print(f"Creating preview environment for PR #{pr_number} (stack: {stack_name})...")

    # Configure lightweight resources for preview
    preview_config = {
        "precision-genomics:db_tier": auto.ConfigValue(value="db-f1-micro"),
        "precision-genomics:experiment_name": auto.ConfigValue(
            value=f"preview-pr-{pr_number}"
        ),
    }
    await stack.set_all_config(preview_config)

    up_result = await stack.up(on_output=print)

    outputs = {k: v.value for k, v in up_result.outputs.items()}

    print(f"\nPreview environment ready!")
    print(f"  API:    {outputs.get('api_url')}")
    print(f"  MCP:    {outputs.get('mcp_sse_url')}")
    print(f"  Worker: {outputs.get('activity_worker_url')}")

    return outputs


async def destroy_preview(pr_number: int) -> None:
    """Tear down the preview environment for a closed/merged PR.

    Destroys all resources and removes the stack entirely.

    Args:
        pr_number: GitHub PR number.
    """
    stack_name = _stack_name(pr_number)

    print(f"Destroying preview environment for PR #{pr_number} (stack: {stack_name})...")

    stack = await auto.create_or_select_stack(
        stack_name=stack_name,
        project_name=PROJECT_NAME,
        work_dir=INFRA_DIR,
    )

    await stack.destroy(on_output=print)
    await stack.workspace.remove_stack(stack_name)

    print(f"Preview environment for PR #{pr_number} destroyed.")


def main():
    parser = argparse.ArgumentParser(
        description="Manage ephemeral PR preview environments"
    )
    parser.add_argument(
        "action", choices=["create", "destroy"],
        help="Create or destroy a preview environment",
    )
    parser.add_argument("--pr", type=int, required=True, help="PR number")
    args = parser.parse_args()

    if args.action == "create":
        asyncio.run(create_preview(args.pr))
    else:
        asyncio.run(destroy_preview(args.pr))


if __name__ == "__main__":
    main()
