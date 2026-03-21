"""GCS buckets for genomics data, ML models, and eval fixtures."""

import pulumi
import pulumi_gcp as gcp


class GCSBuckets(pulumi.ComponentResource):
    """Three GCS buckets: data, models (with lifecycle), and eval fixtures."""

    data_bucket_name: pulumi.Output[str]
    model_bucket_name: pulumi.Output[str]
    eval_fixtures_bucket_name: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        project_id: str,
        region: str,
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("genomics:infra:GCSBuckets", name, None, opts)

        child = pulumi.ResourceOptions(parent=self)

        self.data_bucket = gcp.storage.Bucket(
            f"{name}-data",
            name=f"{project_id}-genomics-data",
            project=project_id,
            location=region,
            uniform_bucket_level_access=True,
            force_destroy=False,
            versioning=gcp.storage.BucketVersioningArgs(enabled=True),
            opts=child,
        )

        self.model_bucket = gcp.storage.Bucket(
            f"{name}-models",
            name=f"{project_id}-genomics-models",
            project=project_id,
            location=region,
            uniform_bucket_level_access=True,
            force_destroy=False,
            versioning=gcp.storage.BucketVersioningArgs(enabled=True),
            lifecycle_rules=[
                gcp.storage.BucketLifecycleRuleArgs(
                    condition=gcp.storage.BucketLifecycleRuleConditionArgs(
                        num_newer_versions=5,
                    ),
                    action=gcp.storage.BucketLifecycleRuleActionArgs(type="Delete"),
                )
            ],
            opts=child,
        )

        self.eval_fixtures_bucket = gcp.storage.Bucket(
            f"{name}-eval-fixtures",
            name=f"{project_id}-genomics-eval-fixtures",
            project=project_id,
            location=region,
            uniform_bucket_level_access=True,
            force_destroy=False,
            opts=child,
        )

        self.data_bucket_name = self.data_bucket.name
        self.model_bucket_name = self.model_bucket.name
        self.eval_fixtures_bucket_name = self.eval_fixtures_bucket.name

        self.register_outputs(
            {
                "data_bucket_name": self.data_bucket_name,
                "model_bucket_name": self.model_bucket_name,
                "eval_fixtures_bucket_name": self.eval_fixtures_bucket_name,
            }
        )
