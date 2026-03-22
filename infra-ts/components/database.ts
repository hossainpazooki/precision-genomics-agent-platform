import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";

export class CloudSQLDatabase extends pulumi.ComponentResource {
  public readonly connectionName: pulumi.Output<string>;
  public readonly privateIp: pulumi.Output<string>;

  constructor(
    name: string,
    args: {
      projectId: string;
      region: string;
      networkId: pulumi.Input<string>;
      dbPassword: pulumi.Input<string>;
      dbTier: string;
    },
    opts?: pulumi.ComponentResourceOptions,
  ) {
    super("genomics:infra:CloudSQLDatabase", name, {}, opts);
    const child = { parent: this };

    const instance = new gcp.sql.DatabaseInstance(`${name}-instance`, {
      name: "precision-genomics-db",
      project: args.projectId,
      region: args.region,
      databaseVersion: "POSTGRES_16",
      deletionProtection: true,
      settings: {
        tier: args.dbTier,
        ipConfiguration: {
          ipv4Enabled: false,
          privateNetwork: args.networkId,
          enablePrivatePathForGoogleCloudServices: true,
        },
        backupConfiguration: {
          enabled: true,
          pointInTimeRecoveryEnabled: true,
        },
        availabilityType: "REGIONAL",
        diskAutoresize: true,
        diskSize: 20,
      },
    }, child);

    new gcp.sql.Database(`${name}-db`, {
      name: "precision_genomics",
      project: args.projectId,
      instance: instance.name,
    }, child);

    new gcp.sql.User(`${name}-user`, {
      name: "app",
      project: args.projectId,
      instance: instance.name,
      password: args.dbPassword,
    }, child);

    this.connectionName = instance.connectionName;
    this.privateIp = instance.privateIpAddress;

    this.registerOutputs({
      connectionName: this.connectionName,
      privateIp: this.privateIp,
    });
  }
}
