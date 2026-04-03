import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";

export class SecretStore extends pulumi.ComponentResource {
  public readonly anthropicKeySecretId: pulumi.Output<string>;
  public readonly dbPasswordSecretId: pulumi.Output<string>;

  constructor(
    name: string,
    args: {
      projectId: string;
      anthropicApiKey: pulumi.Input<string>;
      dbPassword: pulumi.Input<string>;
    },
    opts?: pulumi.ComponentResourceOptions,
  ) {
    super("genomics:infra:SecretStore", name, {}, opts);
    const child = { parent: this };

    const anthropicSecret = new gcp.secretmanager.Secret(`${name}-anthropic`, {
      secretId: "anthropic-api-key",
      project: args.projectId,
      replication: { auto: {} },
    }, child);

    new gcp.secretmanager.SecretVersion(`${name}-anthropic-version`, {
      secret: anthropicSecret.id,
      secretData: args.anthropicApiKey,
    }, child);

    const dbSecret = new gcp.secretmanager.Secret(`${name}-db-password`, {
      secretId: "database-password",
      project: args.projectId,
      replication: { auto: {} },
    }, child);

    new gcp.secretmanager.SecretVersion(`${name}-db-password-version`, {
      secret: dbSecret.id,
      secretData: args.dbPassword,
    }, child);

    this.anthropicKeySecretId = anthropicSecret.secretId;
    this.dbPasswordSecretId = dbSecret.secretId;

    this.registerOutputs({
      anthropicKeySecretId: this.anthropicKeySecretId,
      dbPasswordSecretId: this.dbPasswordSecretId,
    });
  }
}
