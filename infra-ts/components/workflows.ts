import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";
import * as fs from "fs";
import * as path from "path";

export class GenomicsWorkflows extends pulumi.ComponentResource {
  public readonly biomarkerDiscoveryId: pulumi.Output<string>;
  public readonly sampleQcId: pulumi.Output<string>;
  public readonly promptOptimizationId: pulumi.Output<string>;

  constructor(
    name: string,
    args: {
      projectId: string;
      region: string;
      activityServiceUrl: pulumi.Input<string>;
    },
    opts?: pulumi.ComponentResourceOptions,
  ) {
    super("genomics:infra:GenomicsWorkflows", name, {}, opts);
    const child = { parent: this };

    // Service account for workflows
    const sa = new gcp.serviceaccount.Account(`${name}-sa`, {
      accountId: "genomics-workflows",
      project: args.projectId,
      displayName: "Genomics Workflows Service Account",
    }, child);

    // Grant Cloud Run invoker role
    new gcp.projects.IAMMember(`${name}-sa-run-invoker`, {
      project: args.projectId,
      role: "roles/run.invoker",
      member: pulumi.interpolate`serviceAccount:${sa.email}`,
    }, child);

    // Load workflow YAML files
    const workflowsDir = path.join(__dirname, "..", "..", "workflows", "definitions");
    const loadYaml = (filename: string): string => {
      try {
        return fs.readFileSync(path.join(workflowsDir, filename), "utf-8");
      } catch {
        return `main:\n  steps:\n    - init:\n        assign:\n          - status: "placeholder"`;
      }
    };

    const biomarkerWorkflow = new gcp.workflows.Workflow(`${name}-biomarker`, {
      name: "biomarker-discovery",
      project: args.projectId,
      region: args.region,
      serviceAccount: sa.email,
      sourceContents: loadYaml("biomarker_discovery.yaml"),
    }, child);

    const sampleQcWorkflow = new gcp.workflows.Workflow(`${name}-sample-qc`, {
      name: "sample-qc",
      project: args.projectId,
      region: args.region,
      serviceAccount: sa.email,
      sourceContents: loadYaml("sample_qc.yaml"),
    }, child);

    const promptOptWorkflow = new gcp.workflows.Workflow(`${name}-prompt-opt`, {
      name: "prompt-optimization",
      project: args.projectId,
      region: args.region,
      serviceAccount: sa.email,
      sourceContents: loadYaml("prompt_optimization.yaml"),
    }, child);

    this.biomarkerDiscoveryId = biomarkerWorkflow.name;
    this.sampleQcId = sampleQcWorkflow.name;
    this.promptOptimizationId = promptOptWorkflow.name;

    this.registerOutputs({
      biomarkerDiscoveryId: this.biomarkerDiscoveryId,
      sampleQcId: this.sampleQcId,
      promptOptimizationId: this.promptOptimizationId,
    });
  }
}
