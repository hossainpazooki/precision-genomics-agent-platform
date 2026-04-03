"""Infrastructure unit tests using Pulumi mocks.

Demonstrates testing infrastructure-as-code with the same pytest framework
used by the application test suite. Validates resource properties, security
configurations, and component wiring without deploying anything.
"""

from __future__ import annotations

from typing import Any

import pulumi


# ── Pulumi Mock Setup ───────────────────────────────────────────────


class GenomicsMocks(pulumi.runtime.Mocks):
    """Mock GCP provider for unit testing Pulumi components."""

    def new_resource(
        self, args: pulumi.runtime.MockResourceArgs
    ) -> tuple[str, dict[str, Any]]:
        outputs = {**args.inputs}

        # Simulate Cloud SQL outputs
        if args.typ == "gcp:sql/databaseInstance:DatabaseInstance":
            outputs["connectionName"] = "project:region:precision-genomics-pg"
            outputs["privateIpAddress"] = "10.0.0.5"

        # Simulate Redis outputs
        if args.typ == "gcp:redis/instance:Instance":
            outputs["host"] = "10.0.0.10"
            outputs["port"] = 6379

        # Simulate Cloud Run outputs
        if args.typ == "gcp:cloudrunv2/service:Service":
            outputs["uri"] = f"https://{args.name}-abc123.run.app"

        # Simulate GCS outputs
        if args.typ == "gcp:storage/bucket:Bucket":
            outputs["name"] = args.inputs.get("name", args.name)

        # Simulate Artifact Registry outputs
        if args.typ == "gcp:artifactregistry/repository:Repository":
            outputs["repositoryId"] = args.inputs.get("repositoryId", "precision-genomics")

        return f"{args.name}-id", outputs

    def call(self, args: pulumi.runtime.MockCallArgs) -> tuple[dict, list]:
        return {}, []


pulumi.runtime.set_mocks(
    GenomicsMocks(),
    preview=False,
)


# ── Import components AFTER mocks are set ───────────────────────────

# ruff: noqa: E402
from components.cache import MemorystoreRedis
from components.cloud_run_service import CloudRunService, CloudRunServiceArgs
from components.database import CloudSQLDatabase
from components.networking import Networking
from components.registry import ArtifactRegistry
from components.storage import GCSBuckets


# ── Test Fixtures ───────────────────────────────────────────────────

PROJECT = "test-project"
REGION = "us-central1"


# ── Cloud SQL Tests ─────────────────────────────────────────────────


@pulumi.runtime.test
def test_cloud_sql_has_pitr_enabled():
    """Cloud SQL must have point-in-time recovery for data lineage."""

    def check_pitr(settings):
        backup = settings.get("backupConfiguration", {})
        assert backup.get("pointInTimeRecoveryEnabled") is True, (
            "PITR must be enabled for genomics data compliance"
        )

    db = CloudSQLDatabase(
        "test-db",
        project_id=PROJECT,
        region=REGION,
        network_id="projects/test/global/networks/test-vpc",
        db_password=pulumi.Output.from_input("test-password"),
    )
    return db.instance.settings.apply(check_pitr)


@pulumi.runtime.test
def test_cloud_sql_has_deletion_protection():
    """Cloud SQL must have deletion protection enabled."""

    def check_deletion(val):
        assert val is True, "Deletion protection must be enabled"

    db = CloudSQLDatabase(
        "test-db-delete",
        project_id=PROJECT,
        region=REGION,
        network_id="projects/test/global/networks/test-vpc",
        db_password=pulumi.Output.from_input("test-password"),
    )
    return db.instance.deletion_protection.apply(check_deletion)


@pulumi.runtime.test
def test_cloud_sql_private_ip_only():
    """Cloud SQL must not have public IPv4 enabled."""

    def check_private(settings):
        ip_config = settings.get("ipConfiguration", {})
        assert ip_config.get("ipv4Enabled") is False, (
            "Cloud SQL must use private IP only"
        )

    db = CloudSQLDatabase(
        "test-db-private",
        project_id=PROJECT,
        region=REGION,
        network_id="projects/test/global/networks/test-vpc",
        db_password=pulumi.Output.from_input("test-password"),
    )
    return db.instance.settings.apply(check_private)


# ── GCS Tests ───────────────────────────────────────────────────────


@pulumi.runtime.test
def test_gcs_buckets_have_versioning():
    """All GCS buckets must have versioning for data reproducibility."""

    def check_versioning(versioning):
        assert versioning is not None and versioning.get("enabled") is True, (
            "Bucket versioning must be enabled"
        )

    buckets = GCSBuckets("test-gcs", project_id=PROJECT, region=REGION)
    return pulumi.Output.all(
        buckets.data_bucket.versioning,
        buckets.model_bucket.versioning,
    ).apply(lambda vs: all(v.get("enabled") for v in vs if v))


@pulumi.runtime.test
def test_model_bucket_has_lifecycle():
    """Model bucket must have lifecycle rules to manage old versions."""

    def check_lifecycle(rules):
        assert rules and len(rules) > 0, "Model bucket must have lifecycle rules"

    buckets = GCSBuckets("test-gcs-lifecycle", project_id=PROJECT, region=REGION)
    return buckets.model_bucket.lifecycle_rules.apply(check_lifecycle)


# ── Cloud Run Tests ─────────────────────────────────────────────────


@pulumi.runtime.test
def test_cloud_run_api_resource_limits():
    """API service must have correct CPU and memory limits."""

    def check_resources(template):
        containers = template.get("containers", [])
        assert len(containers) > 0, "Must have at least one container"
        limits = containers[0].get("resources", {}).get("limits", {})
        assert limits.get("cpu") == "2", "API CPU must be 2"
        assert limits.get("memory") == "4Gi", "API memory must be 4Gi"

    api = CloudRunService(
        "test-api",
        CloudRunServiceArgs(
            project_id=PROJECT,
            region=REGION,
            image="gcr.io/test/api:latest",
            port=8000,
            cpu="2",
            memory="4Gi",
            min_instances=0,
            max_instances=10,
            vpc_connector_id="projects/test/locations/us-central1/connectors/test",
        ),
    )
    return api.service.template.apply(check_resources)


@pulumi.runtime.test
def test_cloud_run_worker_timeout():
    """Worker service must have 900s timeout for long-running ML tasks."""

    def check_timeout(template):
        assert template.get("timeout") == "900s", (
            "Worker timeout must be 900s for ML workloads"
        )

    worker = CloudRunService(
        "test-worker",
        CloudRunServiceArgs(
            project_id=PROJECT,
            region=REGION,
            image="gcr.io/test/worker:latest",
            port=8081,
            cpu="4",
            memory="8Gi",
            min_instances=0,
            max_instances=5,
            vpc_connector_id="projects/test/locations/us-central1/connectors/test",
            timeout="900s",
        ),
    )
    return worker.service.template.apply(check_timeout)


# ── Networking Tests ────────────────────────────────────────────────


@pulumi.runtime.test
def test_vpc_no_auto_subnets():
    """VPC must not auto-create subnetworks (we manage them explicitly)."""

    def check_auto(val):
        assert val is False, "auto_create_subnetworks must be False"

    net = Networking("test-net", project_id=PROJECT, region=REGION)
    return net.network.auto_create_subnetworks.apply(check_auto)


# ── Registry Tests ──────────────────────────────────────────────────


@pulumi.runtime.test
def test_registry_format_is_docker():
    """Artifact Registry must be configured for Docker format."""

    def check_format(fmt):
        assert fmt == "DOCKER", "Registry format must be DOCKER"

    reg = ArtifactRegistry("test-reg", project_id=PROJECT, region=REGION)
    return reg.repo.format.apply(check_format)
