import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";

export class GCSBuckets extends pulumi.ComponentResource {
  public readonly dataBucketName: pulumi.Output<string>;
  public readonly modelBucketName: pulumi.Output<string>;

  constructor(
    name: string,
    args: { projectId: string; region: string },
    opts?: pulumi.ComponentResourceOptions,
  ) {
    super("genomics:infra:GCSBuckets", name, {}, opts);
    const child = { parent: this };

    const dataBucket = new gcp.storage.Bucket(`${name}-data`, {
      name: pulumi.interpolate`${args.projectId}-genomics-data`,
      project: args.projectId,
      location: args.region,
      uniformBucketLevelAccess: true,
      versioning: { enabled: true },
      labels: { "data-classification": "phi", "hipaa-scope": "true" },
    }, child);

    const modelBucket = new gcp.storage.Bucket(`${name}-models`, {
      name: pulumi.interpolate`${args.projectId}-genomics-models`,
      project: args.projectId,
      location: args.region,
      uniformBucketLevelAccess: true,
      versioning: { enabled: true },
      labels: { "data-classification": "internal", "hipaa-scope": "false" },
    }, child);

    this.dataBucketName = dataBucket.name;
    this.modelBucketName = modelBucket.name;

    this.registerOutputs({
      dataBucketName: this.dataBucketName,
      modelBucketName: this.modelBucketName,
    });
  }
}
