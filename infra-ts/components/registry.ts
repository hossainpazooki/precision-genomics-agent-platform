import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";

export class ArtifactRegistry extends pulumi.ComponentResource {
  public readonly registryUrl: pulumi.Output<string>;

  constructor(
    name: string,
    args: { projectId: string; region: string },
    opts?: pulumi.ComponentResourceOptions,
  ) {
    super("genomics:infra:ArtifactRegistry", name, {}, opts);

    const repo = new gcp.artifactregistry.Repository(`${name}-repo`, {
      repositoryId: "precision-genomics",
      project: args.projectId,
      location: args.region,
      format: "DOCKER",
      labels: { service: "precision-genomics" },
    }, { parent: this });

    this.registryUrl = pulumi.interpolate`${args.region}-docker.pkg.dev/${args.projectId}/${repo.repositoryId}`;

    this.registerOutputs({ registryUrl: this.registryUrl });
  }
}
