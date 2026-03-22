import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";

export class Networking extends pulumi.ComponentResource {
  public readonly networkId: pulumi.Output<string>;
  public readonly subnetId: pulumi.Output<string>;
  public readonly vpcConnectorId: pulumi.Output<string>;

  constructor(
    name: string,
    args: { projectId: string; region: string },
    opts?: pulumi.ComponentResourceOptions,
  ) {
    super("genomics:infra:Networking", name, {}, opts);
    const child = { parent: this };

    const network = new gcp.compute.Network(`${name}-vpc`, {
      name: "precision-genomics-vpc",
      project: args.projectId,
      autoCreateSubnetworks: false,
    }, child);

    const subnet = new gcp.compute.Subnetwork(`${name}-subnet`, {
      name: "precision-genomics-subnet",
      project: args.projectId,
      region: args.region,
      network: network.id,
      ipCidrRange: "10.0.0.0/20",
    }, child);

    const privateIp = new gcp.compute.GlobalAddress(`${name}-private-ip`, {
      name: "precision-genomics-private-ip",
      project: args.projectId,
      purpose: "VPC_PEERING",
      addressType: "INTERNAL",
      prefixLength: 16,
      network: network.id,
    }, child);

    new gcp.servicenetworking.Connection(`${name}-private-vpc`, {
      network: network.id,
      service: "servicenetworking.googleapis.com",
      reservedPeeringRanges: [privateIp.name],
    }, child);

    const vpcConnector = new gcp.vpcaccess.Connector(`${name}-connector`, {
      name: "precision-genomics-vpc",
      project: args.projectId,
      region: args.region,
      ipCidrRange: "10.8.0.0/28",
      network: network.name,
    }, child);

    this.networkId = network.id;
    this.subnetId = subnet.id;
    this.vpcConnectorId = vpcConnector.id;

    this.registerOutputs({
      networkId: this.networkId,
      subnetId: this.subnetId,
      vpcConnectorId: this.vpcConnectorId,
    });
  }
}
