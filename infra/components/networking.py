"""VPC networking: network, subnet, private service access, VPC connector."""

import pulumi
import pulumi_gcp as gcp


class Networking(pulumi.ComponentResource):
    """Private VPC with Cloud Run connector and service networking peering."""

    network_id: pulumi.Output[str]
    subnet_id: pulumi.Output[str]
    vpc_connector_id: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        project_id: str,
        region: str,
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("genomics:infra:Networking", name, None, opts)

        child = pulumi.ResourceOptions(parent=self)

        self.network = gcp.compute.Network(
            f"{name}-vpc",
            name="precision-genomics-vpc",
            project=project_id,
            auto_create_subnetworks=False,
            opts=child,
        )

        self.subnet = gcp.compute.Subnetwork(
            f"{name}-subnet",
            name="precision-genomics-subnet",
            project=project_id,
            region=region,
            network=self.network.id,
            ip_cidr_range="10.0.0.0/20",
            opts=child,
        )

        private_ip = gcp.compute.GlobalAddress(
            f"{name}-private-ip",
            name="precision-genomics-private-ip",
            project=project_id,
            purpose="VPC_PEERING",
            address_type="INTERNAL",
            prefix_length=16,
            network=self.network.id,
            opts=child,
        )

        self.peering = gcp.servicenetworking.Connection(
            f"{name}-private-vpc",
            network=self.network.id,
            service="servicenetworking.googleapis.com",
            reserved_peering_ranges=[private_ip.name],
            opts=child,
        )

        self.vpc_connector = gcp.vpcaccess.Connector(
            f"{name}-connector",
            name="precision-genomics-vpc",
            project=project_id,
            region=region,
            ip_cidr_range="10.8.0.0/28",
            network=self.network.name,
            opts=child,
        )

        self.network_id = self.network.id
        self.subnet_id = self.subnet.id
        self.vpc_connector_id = self.vpc_connector.id

        self.register_outputs(
            {
                "network_id": self.network_id,
                "subnet_id": self.subnet_id,
                "vpc_connector_id": self.vpc_connector_id,
            }
        )
