"""Precision Genomics Agent Platform — Pulumi Infrastructure.

Replaces terraform/main.tf + terraform/outputs.tf.
Wires all ComponentResources together with the same dependency graph
as the original Terraform configuration.
"""

import pulumi

from components import (
    ArtifactRegistry,
    CloudRunService,
    CloudRunServiceArgs,
    CloudSQLDatabase,
    GCSBuckets,
    MemorystoreRedis,
    Networking,
    SecretStore,
    VertexAI,
)
from config import load_config

cfg = load_config()

# --- Networking (no dependencies) ---
networking = Networking("networking", project_id=cfg.project_id, region=cfg.region)

# --- Storage & Registry (no dependencies) ---
gcs = GCSBuckets("gcs", project_id=cfg.project_id, region=cfg.region)
registry = ArtifactRegistry("registry", project_id=cfg.project_id, region=cfg.region)

# --- Secrets ---
secrets = SecretStore(
    "secrets",
    project_id=cfg.project_id,
    anthropic_api_key=cfg.anthropic_api_key,
    db_password=cfg.db_password,
)

# --- Database (depends on networking) ---
database = CloudSQLDatabase(
    "database",
    project_id=cfg.project_id,
    region=cfg.region,
    network_id=networking.network_id,
    db_password=cfg.db_password,
    db_tier=cfg.db_tier,
)

# --- Cache (depends on networking) ---
cache = MemorystoreRedis(
    "cache",
    project_id=cfg.project_id,
    region=cfg.region,
    network_id=networking.network_id,
)

# --- Shared environment variables for Cloud Run services ---
_common_env = {
    "ENVIRONMENT": "production",
    "GCP_PROJECT_ID": cfg.project_id,
    "GCS_DATA_BUCKET": gcs.data_bucket_name,
    "GCS_MODEL_BUCKET": gcs.model_bucket_name,
    "USE_SECRET_MANAGER": "true",
}

_common_secrets = {
    "ANTHROPIC_API_KEY": secrets.anthropic_key_secret_id,
}

_data_service_secrets = {
    **_common_secrets,
    "DATABASE_PASSWORD": secrets.db_password_secret_id,
}

# --- Cloud Run: API ---
api_service = CloudRunService(
    "precision-genomics-api",
    CloudRunServiceArgs(
        project_id=cfg.project_id,
        region=cfg.region,
        image=registry.registry_url.apply(lambda url: f"{url}/api:latest"),
        port=8000,
        cpu="2",
        memory="4Gi",
        min_instances=0,
        max_instances=10,
        vpc_connector_id=networking.vpc_connector_id,
        env_vars={
            **_common_env,
            "REDIS_URL": pulumi.Output.all(cache.host, cache.port).apply(
                lambda args: f"redis://{args[0]}:{args[1]}/0"
            ),
            "CLOUD_SQL_INSTANCE": database.connection_name,
            "PERSIST_MODELS": "true",
        },
        secrets=_data_service_secrets,
    ),
)

# --- Cloud Run: MCP SSE ---
mcp_service = CloudRunService(
    "precision-genomics-mcp-sse",
    CloudRunServiceArgs(
        project_id=cfg.project_id,
        region=cfg.region,
        image=registry.registry_url.apply(lambda url: f"{url}/mcp-sse:latest"),
        port=8080,
        cpu="1",
        memory="2Gi",
        min_instances=1,
        max_instances=5,
        vpc_connector_id=networking.vpc_connector_id,
        env_vars=_common_env,
        secrets=_common_secrets,
        allow_unauthenticated=True,
    ),
)

# --- Cloud Run: Activity Worker ---
worker_service = CloudRunService(
    "precision-genomics-worker",
    CloudRunServiceArgs(
        project_id=cfg.project_id,
        region=cfg.region,
        image=registry.registry_url.apply(lambda url: f"{url}/worker:latest"),
        port=8081,
        cpu="4",
        memory="8Gi",
        min_instances=0,
        max_instances=5,
        vpc_connector_id=networking.vpc_connector_id,
        env_vars={
            **_common_env,
            "REDIS_URL": pulumi.Output.all(cache.host, cache.port).apply(
                lambda args: f"redis://{args[0]}:{args[1]}/0"
            ),
            "CLOUD_SQL_INSTANCE": database.connection_name,
        },
        secrets=_data_service_secrets,
        timeout="900s",
    ),
)

# --- Vertex AI ---
vertex = VertexAI("vertex-ai", project_id=cfg.project_id, region=cfg.region)

# --- Exports (replaces terraform/outputs.tf) ---
# Note: GCP Workflows removed — orchestration migrated to web/src/lib/workflows/engine.ts
pulumi.export("api_url", api_service.url)
pulumi.export("mcp_sse_url", mcp_service.url)
pulumi.export("activity_worker_url", worker_service.url)
pulumi.export("cloud_sql_connection_name", database.connection_name)
pulumi.export("cloud_sql_private_ip", database.private_ip)
pulumi.export("redis_host", cache.host)
pulumi.export("gcs_data_bucket", gcs.data_bucket_name)
pulumi.export("gcs_model_bucket", gcs.model_bucket_name)
pulumi.export("registry_url", registry.registry_url)
