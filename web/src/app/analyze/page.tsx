"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type WorkflowType = "biomarker_discovery" | "sample_qc";

export default function AnalyzePage() {
  const router = useRouter();
  const [workflowType, setWorkflowType] =
    useState<WorkflowType>("biomarker_discovery");
  const [target, setTarget] = useState("msi");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const endpoint =
      workflowType === "biomarker_discovery"
        ? "/api/analyze/biomarkers"
        : "/api/analyze/sample-qc";

    const body =
      workflowType === "biomarker_discovery"
        ? { target, modalities: ["proteomics", "rnaseq"], n_top_features: 30 }
        : { dataset: "train", classification_methods: ["ensemble"] };

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.workflow_id) {
        router.push(`/workflows/${data.workflow_id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start workflow");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">New Analysis</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">
            Workflow Type
          </label>
          <select
            value={workflowType}
            onChange={(e) => setWorkflowType(e.target.value as WorkflowType)}
            className="w-full rounded-md border border-[var(--border)] bg-[var(--card)] p-2"
          >
            <option value="biomarker_discovery">Biomarker Discovery</option>
            <option value="sample_qc">Sample QC</option>
          </select>
        </div>

        {workflowType === "biomarker_discovery" && (
          <div>
            <label className="block text-sm font-medium mb-1">Target</label>
            <select
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className="w-full rounded-md border border-[var(--border)] bg-[var(--card)] p-2"
            >
              <option value="msi">MSI (Microsatellite Instability)</option>
              <option value="gender">Gender</option>
              <option value="mismatch">Mismatch Detection</option>
            </select>
          </div>
        )}

        {error && (
          <div className="rounded-md bg-red-50 text-red-700 p-3 text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] py-2 px-4 font-medium hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Starting..." : "Start Analysis"}
        </button>
      </form>
    </div>
  );
}
