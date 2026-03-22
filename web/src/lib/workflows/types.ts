export type WorkflowStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type WorkflowType =
  | "biomarker_discovery"
  | "sample_qc"
  | "prompt_optimization"
  | "cosmo_pipeline";

export interface WorkflowPhase {
  name: string;
  activity: (ctx: WorkflowContext) => Promise<Record<string, unknown>>;
}

export interface WorkflowContext {
  workflowId: string;
  workflowType: WorkflowType;
  params: Record<string, unknown>;
  results: Map<string, Record<string, unknown>>;
}

export interface WorkflowDefinition {
  type: WorkflowType;
  phases: WorkflowPhase[];
}
