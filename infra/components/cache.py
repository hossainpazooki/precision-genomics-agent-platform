"""Memorystore Redis 7 for caching and feature store state."""

import pulumi
import pulumi_gcp as gcp


class MemorystoreRedis(pulumi.ComponentResource):
    """Redis 7 instance on Memorystore with LRU eviction."""

    host: pulumi.Output[str]
    port: pulumi.Output[int]

    def __init__(
        self,
        name: str,
        project_id: str,
        region: str,
        network_id: pulumi.Input[str],
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("genomics:infra:MemorystoreRedis", name, None, opts)

        self.instance = gcp.redis.Instance(
            f"{name}-redis",
            name="precision-genomics-redis",
            project=project_id,
            region=region,
            tier="BASIC",
            memory_size_gb=1,
            redis_version="REDIS_7_0",
            authorized_network=network_id,
            redis_configs={"maxmemory-policy": "allkeys-lru"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.host = self.instance.host
        self.port = self.instance.port

        self.register_outputs({"host": self.host, "port": self.port})
