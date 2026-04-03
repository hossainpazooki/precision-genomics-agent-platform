"""GCP Secret Manager secrets for API keys and database credentials."""

import pulumi
import pulumi_gcp as gcp


class SecretStore(pulumi.ComponentResource):
    """Manages secrets in GCP Secret Manager with automatic versioning."""

    anthropic_key_secret_id: pulumi.Output[str]
    db_password_secret_id: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        project_id: str,
        anthropic_api_key: pulumi.Output[str],
        db_password: pulumi.Output[str],
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("genomics:infra:SecretStore", name, None, opts)

        child = pulumi.ResourceOptions(parent=self)

        anthropic_secret = gcp.secretmanager.Secret(
            f"{name}-anthropic-key",
            secret_id="ANTHROPIC_API_KEY",
            project=project_id,
            replication=gcp.secretmanager.SecretReplicationArgs(
                auto=gcp.secretmanager.SecretReplicationAutoArgs(),
            ),
            opts=child,
        )

        gcp.secretmanager.SecretVersion(
            f"{name}-anthropic-key-version",
            secret=anthropic_secret.id,
            secret_data=anthropic_api_key,
            opts=child,
        )

        db_secret = gcp.secretmanager.Secret(
            f"{name}-db-password",
            secret_id="DATABASE_PASSWORD",
            project=project_id,
            replication=gcp.secretmanager.SecretReplicationArgs(
                auto=gcp.secretmanager.SecretReplicationAutoArgs(),
            ),
            opts=child,
        )

        gcp.secretmanager.SecretVersion(
            f"{name}-db-password-version",
            secret=db_secret.id,
            secret_data=db_password,
            opts=child,
        )

        self.anthropic_key_secret_id = anthropic_secret.secret_id
        self.db_password_secret_id = db_secret.secret_id

        self.register_outputs(
            {
                "anthropic_key_secret_id": self.anthropic_key_secret_id,
                "db_password_secret_id": self.db_password_secret_id,
            }
        )
