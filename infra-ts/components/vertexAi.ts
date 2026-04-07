// Note: AiMetadataStore intentionally omitted — google-beta provider bug
// causes a perpetual create/destroy cycle. See DEPLOY.md for history.

import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";

export class VertexAI extends pulumi.ComponentResource {
  public readonly tensorboardName: pulumi.Output<string>;

  constructor(
    name: string,
    args: { projectId: string; region: string },
    opts?: pulumi.ComponentResourceOptions,
  ) {
    super("genomics:infra:VertexAI", name, {}, opts);
    const child = { parent: this };

    const tensorboard = new gcp.vertex.AiTensorboard(`${name}-tensorboard`, {
      displayName: "precision-genomics-tensorboard",
      project: args.projectId,
      region: args.region,
    }, child);

    this.tensorboardName = tensorboard.name;

    this.registerOutputs({
      tensorboardName: this.tensorboardName,
    });
  }
}
