"""Cloud SQL PostgreSQL 15 with private networking, PITR, and app user."""

import pulumi
import pulumi_gcp as gcp


class CloudSQLDatabase(pulumi.ComponentResource):
    """Cloud SQL PostgreSQL instance with database and application user."""

    connection_name: pulumi.Output[str]
    private_ip: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        project_id: str,
        region: str,
        network_id: pulumi.Input[str],
        db_password: pulumi.Output[str],
        db_tier: str = "db-custom-2-8192",
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("genomics:infra:CloudSQLDatabase", name, None, opts)

        child = pulumi.ResourceOptions(parent=self)

        self.instance = gcp.sql.DatabaseInstance(
            f"{name}-instance",
            name="precision-genomics-pg",
            project=project_id,
            region=region,
            database_version="POSTGRES_15",
            deletion_protection=True,
            settings=gcp.sql.DatabaseInstanceSettingsArgs(
                tier=db_tier,
                availability_type="ZONAL",
                disk_size=20,
                ip_configuration=gcp.sql.DatabaseInstanceSettingsIpConfigurationArgs(
                    ipv4_enabled=False,
                    private_network=network_id,
                ),
                backup_configuration=gcp.sql.DatabaseInstanceSettingsBackupConfigurationArgs(
                    enabled=True,
                    point_in_time_recovery_enabled=True,
                ),
                database_flags=[
                    gcp.sql.DatabaseInstanceSettingsDatabaseFlagArgs(
                        name="max_connections",
                        value="100",
                    )
                ],
            ),
            opts=child,
        )

        gcp.sql.Database(
            f"{name}-db",
            name="precision_genomics",
            instance=self.instance.name,
            project=project_id,
            opts=child,
        )

        gcp.sql.User(
            f"{name}-user",
            name="app",
            instance=self.instance.name,
            project=project_id,
            password=db_password,
            opts=child,
        )

        self.connection_name = self.instance.connection_name
        self.private_ip = self.instance.private_ip_address

        self.register_outputs(
            {
                "connection_name": self.connection_name,
                "private_ip": self.private_ip,
            }
        )
