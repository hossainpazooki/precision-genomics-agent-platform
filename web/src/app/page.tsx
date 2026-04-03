import Link from "next/link";

async function getStats() {
  try {
    const base = process.env.NEXT_PUBLIC_BASE_URL ?? "http://localhost:3000";
    const [panelsRes, healthRes] = await Promise.all([
      fetch(`${base}/api/biomarkers/panels`, { cache: "no-store" }).catch(
        () => null,
      ),
      fetch(`${base}/api/health`, { cache: "no-store" }).catch(() => null),
    ]);
    const panels = panelsRes?.ok ? await panelsRes.json() : [];
    const health = healthRes?.ok ? await healthRes.json() : { status: "unknown" };
    return { panels, health };
  } catch {
    return { panels: [], health: { status: "unknown" } };
  }
}

export default async function DashboardPage() {
  const { panels, health } = await getStats();

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold mb-2">Dashboard</h2>
        <p className="text-[var(--muted-foreground)]">
          Precision genomics platform for multi-omics biomarker discovery
        </p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-lg border border-[var(--border)] p-4 bg-[var(--card)]">
          <div className="text-sm text-[var(--muted-foreground)]">
            System Status
          </div>
          <div className="text-2xl font-bold mt-1">
            <span
              className={
                health.status === "healthy"
                  ? "text-[var(--success)]"
                  : "text-[var(--warning)]"
              }
            >
              {health.status === "healthy" ? "Healthy" : "Degraded"}
            </span>
          </div>
        </div>

        <div className="rounded-lg border border-[var(--border)] p-4 bg-[var(--card)]">
          <div className="text-sm text-[var(--muted-foreground)]">
            Biomarker Panels
          </div>
          <div className="text-2xl font-bold mt-1">{panels.length}</div>
        </div>

        <div className="rounded-lg border border-[var(--border)] p-4 bg-[var(--card)]">
          <div className="text-sm text-[var(--muted-foreground)]">
            ML Service
          </div>
          <div className="text-2xl font-bold mt-1">
            <span
              className={
                health.services?.ml === "healthy"
                  ? "text-[var(--success)]"
                  : "text-[var(--muted-foreground)]"
              }
            >
              {health.services?.ml ?? "unknown"}
            </span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link
            href="/analyze"
            className="rounded-lg border border-[var(--border)] p-4 bg-[var(--card)] hover:border-[var(--primary)] transition-colors"
          >
            <div className="font-medium">New Analysis</div>
            <div className="text-sm text-[var(--muted-foreground)] mt-1">
              Start a biomarker discovery or sample QC workflow
            </div>
          </Link>

          <Link
            href="/workflows"
            className="rounded-lg border border-[var(--border)] p-4 bg-[var(--card)] hover:border-[var(--primary)] transition-colors"
          >
            <div className="font-medium">View Workflows</div>
            <div className="text-sm text-[var(--muted-foreground)] mt-1">
              Monitor running and completed workflows
            </div>
          </Link>

          <Link
            href="/biomarkers"
            className="rounded-lg border border-[var(--border)] p-4 bg-[var(--card)] hover:border-[var(--primary)] transition-colors"
          >
            <div className="font-medium">Biomarker Panels</div>
            <div className="text-sm text-[var(--muted-foreground)] mt-1">
              Browse discovered biomarker panels and features
            </div>
          </Link>

          <Link
            href="/biomarkers"
            className="rounded-lg border border-[var(--border)] p-4 bg-[var(--card)] hover:border-[var(--primary)] transition-colors"
          >
            <div className="font-medium">Feature Explorer</div>
            <div className="text-sm text-[var(--muted-foreground)] mt-1">
              Explore feature importance and biological annotations
            </div>
          </Link>
        </div>
      </div>

      {/* Recent Panels */}
      {panels.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-3">Recent Panels</h3>
          <div className="rounded-lg border border-[var(--border)] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-[var(--muted)]">
                <tr>
                  <th className="text-left p-3">ID</th>
                  <th className="text-left p-3">Target</th>
                  <th className="text-left p-3">Modality</th>
                  <th className="text-left p-3">Features</th>
                  <th className="text-left p-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {panels.map(
                  (panel: {
                    id: number;
                    target: string;
                    modality: string;
                    n_features: number;
                    created_at: string;
                  }) => (
                    <tr
                      key={panel.id}
                      className="border-t border-[var(--border)]"
                    >
                      <td className="p-3">
                        <Link
                          href={`/biomarkers/${panel.id}`}
                          className="text-[var(--primary)] hover:underline"
                        >
                          #{panel.id}
                        </Link>
                      </td>
                      <td className="p-3">{panel.target}</td>
                      <td className="p-3">{panel.modality}</td>
                      <td className="p-3">{panel.n_features}</td>
                      <td className="p-3 text-[var(--muted-foreground)]">
                        {panel.created_at
                          ? new Date(panel.created_at).toLocaleDateString()
                          : "-"}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
