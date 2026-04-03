"""Artifact Registry for Docker images."""

import pulumi
import pulumi_gcp as gcp


class ArtifactRegistry(pulumi.ComponentResource):
    """Docker container registry in Artifact Registry."""

    registry_url: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        project_id: str,
        region: str,
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("genomics:infra:ArtifactRegistry", name, None, opts)

        self.repo = gcp.artifactregistry.Repository(
            f"{name}-repo",
            project=project_id,
            location=region,
            repository_id="precision-genomics",
            format="DOCKER",
            description="Docker images for Precision Genomics Agent Platform",
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.registry_url = pulumi.Output.concat(
            region, "-docker.pkg.dev/", project_id, "/", self.repo.repository_id
        )

        self.register_outputs({"registry_url": self.registry_url})
