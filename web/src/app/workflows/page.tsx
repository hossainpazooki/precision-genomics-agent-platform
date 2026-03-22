import Link from "next/link";
import { prisma } from "@/lib/prisma";

async function getWorkflows() {
  try {
    return await prisma.workflowExecution.findMany({
      orderBy: { startedAt: "desc" },
      take: 50,
    });
  } catch {
    return [];
  }
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-800",
};

export default async function WorkflowsPage() {
  const workflows = await getWorkflows();

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Workflows</h2>
        <Link
          href="/analyze"
          className="rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] py-2 px-4 text-sm font-medium hover:opacity-90"
        >
          New Analysis
        </Link>
      </div>

      {workflows.length === 0 ? (
        <div className="text-center py-12 text-[var(--muted-foreground)]">
          No workflows yet. Start a new analysis to create one.
        </div>
      ) : (
        <div className="rounded-lg border border-[var(--border)] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[var(--muted)]">
              <tr>
                <th className="text-left p-3">ID</th>
                <th className="text-left p-3">Type</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Phase</th>
                <th className="text-left p-3">Started</th>
              </tr>
            </thead>
            <tbody>
              {workflows.map((wf) => (
                <tr
                  key={wf.id}
                  className="border-t border-[var(--border)] hover:bg-[var(--muted)]/50"
                >
                  <td className="p-3">
                    <Link
                      href={`/workflows/${wf.id}`}
                      className="text-[var(--primary)] hover:underline font-mono text-xs"
                    >
                      {wf.id}
                    </Link>
                  </td>
                  <td className="p-3">{wf.workflowType.replace(/_/g, " ")}</td>
                  <td className="p-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[wf.status] ?? ""}`}
                    >
                      {wf.status}
                    </span>
                  </td>
                  <td className="p-3 text-[var(--muted-foreground)]">
                    {wf.currentPhase}
                  </td>
                  <td className="p-3 text-[var(--muted-foreground)]">
                    {wf.startedAt.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
