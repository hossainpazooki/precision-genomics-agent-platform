"""GCP Workflows for genomics pipeline orchestration.

Deploys three workflow definitions (biomarker discovery, sample QC,
prompt optimization) with a dedicated service account and IAM bindings.
"""

from pathlib import Path

import pulumi
import pulumi_gcp as gcp

# Resolve workflow YAML definitions relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_WORKFLOW_DEFS = _PROJECT_ROOT / "workflows" / "definitions"


class GenomicsWorkflows(pulumi.ComponentResource):
    """GCP Workflows with service account, IAM, and three workflow definitions."""

    biomarker_discovery_id: pulumi.Output[str]
    sample_qc_id: pulumi.Output[str]
    prompt_optimization_id: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        project_id: str,
        region: str,
        activity_service_url: pulumi.Input[str],
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("genomics:infra:GenomicsWorkflows", name, None, opts)

        child = pulumi.ResourceOptions(parent=self)

        # Service account for workflow execution
        sa = gcp.serviceaccount.Account(
            f"{name}-sa",
            project=project_id,
            account_id="precision-genomics-workflows",
            display_name="Precision Genomics Workflows",
            opts=child,
        )

        # IAM: allow the SA to invoke workflows and Cloud Run
        for role_suffix, role in [
            ("workflows-invoker", "roles/workflows.invoker"),
            ("run-invoker", "roles/run.invoker"),
        ]:
            gcp.projects.IAMMember(
                f"{name}-{role_suffix}",
                project=project_id,
                role=role,
                member=sa.email.apply(lambda e: f"serviceAccount:{e}"),
                opts=child,
            )

        # Deploy three workflow definitions
        workflow_specs = {
            "biomarker-discovery": "biomarker_discovery.yaml",
            "sample-qc": "sample_qc.yaml",
            "prompt-optimization": "prompt_optimization.yaml",
        }

        workflows: dict[str, gcp.workflows.Workflow] = {}
        for wf_name, yaml_file in workflow_specs.items():
            source = (_WORKFLOW_DEFS / yaml_file).read_text()
            workflows[wf_name] = gcp.workflows.Workflow(
                f"{name}-{wf_name}",
                name=f"precision-genomics-{wf_name}",
                project=project_id,
                region=region,
                service_account=sa.id,
                source_contents=source,
                opts=child,
            )

        self.biomarker_discovery_id = workflows["biomarker-discovery"].id
        self.sample_qc_id = workflows["sample-qc"].id
        self.prompt_optimization_id = workflows["prompt-optimization"].id

        self.register_outputs(
            {
                "biomarker_discovery_id": self.biomarker_discovery_id,
                "sample_qc_id": self.sample_qc_id,
                "prompt_optimization_id": self.prompt_optimization_id,
            }
        )
