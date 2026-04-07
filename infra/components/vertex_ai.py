"""Vertex AI TensorBoard for experiment tracking.

Note: AiMetadataStore intentionally omitted — google-beta provider bug causes
a perpetual create/destroy cycle. See DEPLOY.md for history.
"""

import pulumi
import pulumi_gcp as gcp


class VertexAI(pulumi.ComponentResource):
    """Vertex AI resources for ML experiment tracking and visualization."""

    tensorboard_id: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        project_id: str,
        region: str,
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("genomics:infra:VertexAI", name, None, opts)

        child = pulumi.ResourceOptions(parent=self)

        self.tensorboard = gcp.vertex.AiTensorboard(
            f"{name}-tensorboard",
            project=project_id,
            region=region,
            display_name="precision-genomics-tensorboard",
            opts=child,
        )

        self.tensorboard_id = self.tensorboard.name

        self.register_outputs(
            {
                "tensorboard_id": self.tensorboard_id,
            }
        )
