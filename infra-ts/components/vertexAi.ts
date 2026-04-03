import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";

export class VertexAI extends pulumi.ComponentResource {
  public readonly metadataStoreName: pulumi.Output<string>;
  public readonly tensorboardName: pulumi.Output<string>;

  constructor(
    name: string,
    args: { projectId: string; region: string },
    opts?: pulumi.ComponentResourceOptions,
  ) {
    super("genomics:infra:VertexAI", name, {}, opts);
    const child = { parent: this };

    const metadataStore = new gcp.vertex.AiMetadataStore(`${name}-metadata`, {
      project: args.projectId,
      region: args.region,
    }, child);

    const tensorboard = new gcp.vertex.AiTensorboard(`${name}-tensorboard`, {
      displayName: "precision-genomics-tensorboard",
      project: args.projectId,
      region: args.region,
    }, child);

    this.metadataStoreName = metadataStore.name;
    this.tensorboardName = tensorboard.name;

    this.registerOutputs({
      metadataStoreName: this.metadataStoreName,
      tensorboardName: this.tensorboardName,
    });
  }
}
