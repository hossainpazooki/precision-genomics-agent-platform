"use client";

import { useParams } from "next/navigation";
import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function WorkflowDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const { data, error, isLoading } = useSWR(
    `/api/analyze/${id}/status`,
    fetcher,
    { refreshInterval: 2000 },
  );

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-[var(--muted-foreground)]">
        Loading workflow...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-red-600">
        Failed to load workflow
      </div>
    );
  }

  const phasesCompleted: string[] = data.phases_completed ?? [];
  const phasesRemaining: string[] = data.phases_remaining ?? [];
  const allPhases = [...phasesCompleted, data.current_phase, ...phasesRemaining].filter(
    (p, i, arr) => p && arr.indexOf(p) === i,
  );

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Workflow Detail</h2>
        <p className="text-sm text-[var(--muted-foreground)] font-mono mt-1">
          {id}
        </p>
      </div>

      {/* Status */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-lg border border-[var(--border)] p-4">
          <div className="text-xs text-[var(--muted-foreground)]">Status</div>
          <div className="text-lg font-semibold mt-1">{data.status}</div>
        </div>
        <div className="rounded-lg border border-[var(--border)] p-4">
          <div className="text-xs text-[var(--muted-foreground)]">Type</div>
          <div className="text-lg font-semibold mt-1">
            {data.workflow_type?.replace(/_/g, " ")}
          </div>
        </div>
        <div className="rounded-lg border border-[var(--border)] p-4">
          <div className="text-xs text-[var(--muted-foreground)]">
            Current Phase
          </div>
          <div className="text-lg font-semibold mt-1">
            {data.current_phase ?? "-"}
          </div>
        </div>
        <div className="rounded-lg border border-[var(--border)] p-4">
          <div className="text-xs text-[var(--muted-foreground)]">
            Started
          </div>
          <div className="text-sm font-medium mt-1">
            {data.started_at
              ? new Date(data.started_at).toLocaleString()
              : "-"}
          </div>
        </div>
      </div>

      {/* Phase Progress */}
      {allPhases.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-3">Phase Progress</h3>
          <div className="space-y-2">
            {allPhases.map((phase) => {
              const isCompleted = phasesCompleted.includes(phase);
              const isCurrent = phase === data.current_phase && !isCompleted;
              return (
                <div
                  key={phase}
                  className={`flex items-center gap-3 rounded-md border p-3 ${
                    isCompleted
                      ? "border-green-200 bg-green-50"
                      : isCurrent
                        ? "border-blue-200 bg-blue-50"
                        : "border-[var(--border)]"
                  }`}
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      isCompleted
                        ? "bg-green-500"
                        : isCurrent
                          ? "bg-blue-500 animate-pulse"
                          : "bg-gray-300"
                    }`}
                  />
                  <span className="text-sm">
                    {phase.replace(/_/g, " ")}
                  </span>
                  {isCompleted && (
                    <span className="text-xs text-green-600 ml-auto">
                      done
                    </span>
                  )}
                  {isCurrent && (
                    <span className="text-xs text-blue-600 ml-auto">
                      running
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Cancel button */}
      {(data.status === "running" || data.status === "pending") && (
        <button
          onClick={async () => {
            await fetch(`/api/workflows/${id}/cancel`, { method: "POST" });
          }}
          className="rounded-md border border-[var(--destructive)] text-[var(--destructive)] py-2 px-4 text-sm hover:bg-red-50"
        >
          Cancel Workflow
        </button>
      )}
    </div>
  );
}
