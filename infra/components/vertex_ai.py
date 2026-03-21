"""Vertex AI metadata store and TensorBoard for experiment tracking."""

import pulumi
import pulumi_gcp as gcp


class VertexAI(pulumi.ComponentResource):
    """Vertex AI resources for ML experiment tracking and visualization."""

    metadata_store_id: pulumi.Output[str]
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

        self.metadata_store = gcp.vertex.AiMetadataStore(
            f"{name}-metadata",
            project=project_id,
            region=region,
            opts=child,
        )

        self.tensorboard = gcp.vertex.AiTensorboard(
            f"{name}-tensorboard",
            project=project_id,
            region=region,
            display_name="precision-genomics-tensorboard",
            opts=child,
        )

        self.metadata_store_id = self.metadata_store.name
        self.tensorboard_id = self.tensorboard.name

        self.register_outputs(
            {
                "metadata_store_id": self.metadata_store_id,
                "tensorboard_id": self.tensorboard_id,
            }
        )
