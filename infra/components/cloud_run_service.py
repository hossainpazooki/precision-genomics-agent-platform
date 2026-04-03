"""Reusable Cloud Run v2 service ComponentResource.

This is the showcase piece — a single typed abstraction instantiated 3 times
(API, MCP SSE, Activity Worker) with different configurations, eliminating
the repetition in the original Terraform module.
"""

from dataclasses import dataclass, field

import pulumi
import pulumi_gcp as gcp


@dataclass
class CloudRunServiceArgs:
    """Typed arguments for a Cloud Run service deployment."""

    project_id: str
    region: str
    image: pulumi.Input[str]
    port: int
    cpu: str
    memory: str
    min_instances: int
    max_instances: int
    vpc_connector_id: pulumi.Input[str]
    env_vars: dict[str, pulumi.Input[str]] = field(default_factory=dict)
    secrets: dict[str, pulumi.Input[str]] = field(default_factory=dict)
    timeout: str = "300s"
    allow_unauthenticated: bool = False


class CloudRunService(pulumi.ComponentResource):
    """A reusable Cloud Run v2 service with VPC, secrets, and scaling.

    Encapsulates the pattern shared by all three platform services:
    - VPC connector for private networking
    - Secret Manager references for sensitive env vars
    - Configurable scaling, CPU, memory, and timeout
    """

    url: pulumi.Output[str]
    service_name: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        args: CloudRunServiceArgs,
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("genomics:infra:CloudRunService", name, None, opts)

        # Build environment variable list: plain env vars + secret references
        env_entries = [
            gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                name=k,
                value=v,
            )
            for k, v in args.env_vars.items()
        ]

        for secret_env_name, secret_id in args.secrets.items():
            env_entries.append(
                gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                    name=secret_env_name,
                    value_source=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceArgs(
                        secret_key_ref=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceSecretKeyRefArgs(
                            secret=secret_id,
                            version="latest",
                        ),
                    ),
                )
            )

        self.service = gcp.cloudrunv2.Service(
            f"{name}-service",
            name=name,
            project=args.project_id,
            location=args.region,
            template=gcp.cloudrunv2.ServiceTemplateArgs(
                containers=[
                    gcp.cloudrunv2.ServiceTemplateContainerArgs(
                        image=args.image,
                        ports=[
                            gcp.cloudrunv2.ServiceTemplateContainerPortArgs(
                                container_port=args.port,
                            )
                        ],
                        envs=env_entries,
                        resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                            limits={"cpu": args.cpu, "memory": args.memory},
                        ),
                    )
                ],
                vpc_access=gcp.cloudrunv2.ServiceTemplateVpcAccessArgs(
                    connector=args.vpc_connector_id,
                    egress="PRIVATE_RANGES_ONLY",
                ),
                scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
                    min_instance_count=args.min_instances,
                    max_instance_count=args.max_instances,
                ),
                timeout=args.timeout,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Optionally allow unauthenticated access (e.g. MCP SSE endpoint)
        if args.allow_unauthenticated:
            gcp.cloudrunv2.ServiceIamMember(
                f"{name}-public-access",
                project=args.project_id,
                location=args.region,
                name=self.service.name,
                role="roles/run.invoker",
                member="allUsers",
                opts=pulumi.ResourceOptions(parent=self),
            )

        self.url = self.service.uri
        self.service_name = self.service.name

        self.register_outputs({"url": self.url, "service_name": self.service_name})
