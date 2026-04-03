import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";

export class MemorystoreRedis extends pulumi.ComponentResource {
  public readonly host: pulumi.Output<string>;
  public readonly port: pulumi.Output<number>;

  constructor(
    name: string,
    args: {
      projectId: string;
      region: string;
      networkId: pulumi.Input<string>;
    },
    opts?: pulumi.ComponentResourceOptions,
  ) {
    super("genomics:infra:MemorystoreRedis", name, {}, opts);

    const instance = new gcp.redis.Instance(`${name}-redis`, {
      name: "precision-genomics-cache",
      project: args.projectId,
      region: args.region,
      tier: "BASIC",
      memorySizeGb: 1,
      redisVersion: "REDIS_7_0",
      authorizedNetwork: args.networkId,
    }, { parent: this });

    this.host = instance.host;
    this.port = instance.port;

    this.registerOutputs({ host: this.host, port: this.port });
  }
}
