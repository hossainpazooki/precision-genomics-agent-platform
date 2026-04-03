"""CrossGuard policy-as-code for genomics platform compliance.

Enforces security, data protection, and operational best practices
relevant to healthcare/genomics workloads. Demonstrates Pulumi's
policy-as-code capabilities with domain-specific guardrails.
"""

from pulumi_policy import (
    EnforcementLevel,
    ResourceValidationArgs,
    ResourceValidationPolicy,
)

# ── Cloud SQL Policies ──────────────────────────────────────────────


def _require_pitr(args: ResourceValidationArgs, report_violation):
    """Cloud SQL instances must have point-in-time recovery for data lineage."""
    if args.resource_type == "gcp:sql/databaseInstance:DatabaseInstance":
        settings = args.props.get("settings", {})
        backup = settings.get("backupConfiguration", {})
        if not backup.get("pointInTimeRecoveryEnabled"):
            report_violation(
                "Cloud SQL instances must have point-in-time recovery enabled "
                "for genomics data lineage and audit compliance."
            )


def _require_deletion_protection(args: ResourceValidationArgs, report_violation):
    """Cloud SQL instances must have deletion protection."""
    if args.resource_type == "gcp:sql/databaseInstance:DatabaseInstance":
        if not args.props.get("deletionProtection"):
            report_violation(
                "Cloud SQL instances must have deletion_protection=true "
                "to prevent accidental data loss."
            )


def _require_private_ip_only(args: ResourceValidationArgs, report_violation):
    """Cloud SQL must use private IP only — no public exposure."""
    if args.resource_type == "gcp:sql/databaseInstance:DatabaseInstance":
        settings = args.props.get("settings", {})
        ip_config = settings.get("ipConfiguration", {})
        if ip_config.get("ipv4Enabled"):
            report_violation(
                "Cloud SQL instances must not have public IPv4 enabled. "
                "Use private networking only."
            )


# ── GCS Policies ────────────────────────────────────────────────────


def _require_bucket_versioning(args: ResourceValidationArgs, report_violation):
    """GCS buckets must have versioning for data reproducibility."""
    if args.resource_type == "gcp:storage/bucket:Bucket":
        versioning = args.props.get("versioning", {})
        if not versioning.get("enabled"):
            report_violation(
                "GCS buckets must have versioning enabled for genomics "
                "data reproducibility and audit trail."
            )


def _deny_force_destroy(args: ResourceValidationArgs, report_violation):
    """GCS buckets must not allow force destroy in production."""
    if args.resource_type == "gcp:storage/bucket:Bucket":
        if args.props.get("forceDestroy"):
            report_violation(
                "GCS buckets must not have force_destroy=true. "
                "Genomics data deletion requires explicit procedures."
            )


# ── Cloud Run Policies ──────────────────────────────────────────────


def _require_vpc_connector(args: ResourceValidationArgs, report_violation):
    """Cloud Run services must use VPC connector for private networking."""
    if args.resource_type == "gcp:cloudrunv2/service:Service":
        template = args.props.get("template", {})
        vpc_access = template.get("vpcAccess", {})
        if not vpc_access.get("connector"):
            report_violation(
                "Cloud Run services must have a VPC connector configured "
                "for private network access to Cloud SQL and Redis."
            )


def _enforce_resource_limits(args: ResourceValidationArgs, report_violation):
    """Cloud Run services must have explicit CPU and memory limits."""
    if args.resource_type == "gcp:cloudrunv2/service:Service":
        template = args.props.get("template", {})
        containers = template.get("containers", [])
        for container in containers:
            resources = container.get("resources", {})
            limits = resources.get("limits", {})
            if not limits.get("cpu") or not limits.get("memory"):
                report_violation(
                    "Cloud Run containers must have explicit CPU and memory "
                    "limits to prevent runaway resource consumption."
                )


# ── Secret Manager Policies ─────────────────────────────────────────


def _require_secret_replication(args: ResourceValidationArgs, report_violation):
    """Secrets must have replication configured."""
    if args.resource_type == "gcp:secretmanager/secret:Secret":
        replication = args.props.get("replication", {})
        if not replication.get("auto") and not replication.get("userManaged"):
            report_violation(
                "Secrets must have replication configured for availability."
            )


# ── Intent Lifecycle Policies ──────────────────────────────────────


def _enforce_training_gpu_limit(
    args: ResourceValidationArgs, report_violation,
) -> None:
    """Training intents must not exceed max GPU count per stack (4 GPUs)."""
    if args.resource_type == "gcp:compute/instance:Instance":
        guest_accelerators = args.props.get("guestAccelerators", [])
        total_gpus = sum(a.get("count", 0) for a in guest_accelerators)
        if total_gpus > 4:
            report_violation(
                f"Training intent GPU limit exceeded: {total_gpus} GPUs requested, "
                "maximum 4 allowed per stack."
            )


def _require_intent_labels(
    args: ResourceValidationArgs, report_violation,
) -> None:
    """Resources provisioned by intents should carry intent tracking labels."""
    intent_resource_types = {
        "gcp:cloudrunv2/service:Service",
        "gcp:compute/instance:Instance",
        "gcp:storage/bucket:Bucket",
    }
    if args.resource_type in intent_resource_types:
        labels = args.props.get("labels", {})
        if not labels.get("intent-id"):
            report_violation(
                "Resources provisioned by intents should carry 'intent-id' "
                "and 'intent-type' labels for audit traceability."
            )


# ── Aggregate Policy List ───────────────────────────────────────────

policies = [
    ResourceValidationPolicy(
        name="cloud-sql-pitr-required",
        description="Cloud SQL must have PITR for genomics data lineage",
        validate=_require_pitr,
        enforcement_level=EnforcementLevel.MANDATORY,
    ),
    ResourceValidationPolicy(
        name="cloud-sql-deletion-protection",
        description="Cloud SQL must have deletion protection",
        validate=_require_deletion_protection,
        enforcement_level=EnforcementLevel.MANDATORY,
    ),
    ResourceValidationPolicy(
        name="cloud-sql-private-only",
        description="Cloud SQL must use private IP only",
        validate=_require_private_ip_only,
        enforcement_level=EnforcementLevel.MANDATORY,
    ),
    ResourceValidationPolicy(
        name="gcs-versioning-required",
        description="GCS buckets must have versioning for data reproducibility",
        validate=_require_bucket_versioning,
        enforcement_level=EnforcementLevel.MANDATORY,
    ),
    ResourceValidationPolicy(
        name="gcs-no-force-destroy",
        description="GCS buckets must not allow force destroy",
        validate=_deny_force_destroy,
        enforcement_level=EnforcementLevel.MANDATORY,
    ),
    ResourceValidationPolicy(
        name="cloud-run-vpc-required",
        description="Cloud Run services must use VPC connector",
        validate=_require_vpc_connector,
        enforcement_level=EnforcementLevel.MANDATORY,
    ),
    ResourceValidationPolicy(
        name="cloud-run-resource-limits",
        description="Cloud Run services must have resource limits",
        validate=_enforce_resource_limits,
        enforcement_level=EnforcementLevel.MANDATORY,
    ),
    ResourceValidationPolicy(
        name="secret-replication-required",
        description="Secrets must have replication configured",
        validate=_require_secret_replication,
        enforcement_level=EnforcementLevel.ADVISORY,
    ),
    # ── Intent Lifecycle Policies ──────────────────────────────────────
    ResourceValidationPolicy(
        name="training-gpu-limit",
        description="Training intents must not exceed 4 GPUs per stack",
        validate=_enforce_training_gpu_limit,
        enforcement_level=EnforcementLevel.MANDATORY,
    ),
    ResourceValidationPolicy(
        name="intent-resource-labels",
        description="Intent-provisioned resources should carry tracking labels",
        validate=_require_intent_labels,
        enforcement_level=EnforcementLevel.ADVISORY,
    ),
]
