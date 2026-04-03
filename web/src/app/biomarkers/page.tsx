import Link from "next/link";

async function getPanels() {
  try {
    const base = process.env.NEXT_PUBLIC_BASE_URL ?? "http://localhost:3000";
    const res = await fetch(`${base}/api/biomarkers/panels`, {
      cache: "no-store",
    });
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}

export default async function BiomarkersPage() {
  const panels = await getPanels();

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">Biomarker Panels</h2>

      {panels.length === 0 ? (
        <div className="text-center py-12 text-[var(--muted-foreground)]">
          No panels discovered yet. Run a biomarker discovery workflow first.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {panels.map(
            (panel: {
              id: number;
              target: string;
              modality: string;
              n_features: number;
              features: Array<{ gene: string; importance: number }>;
              created_at: string;
            }) => (
              <Link
                key={panel.id}
                href={`/biomarkers/${panel.id}`}
                className="rounded-lg border border-[var(--border)] p-4 bg-[var(--card)] hover:border-[var(--primary)] transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">
                    Panel #{panel.id}
                  </span>
                  <span className="text-xs bg-[var(--muted)] px-2 py-0.5 rounded">
                    {panel.modality}
                  </span>
                </div>
                <div className="text-sm text-[var(--muted-foreground)] mb-3">
                  Target: {panel.target} | {panel.n_features} features
                </div>
                {panel.features?.slice(0, 5).map((f) => (
                  <div
                    key={f.gene}
                    className="flex items-center gap-2 text-xs mb-1"
                  >
                    <span className="font-mono w-16">{f.gene}</span>
                    <div className="flex-1 bg-[var(--muted)] rounded-full h-2">
                      <div
                        className="bg-[var(--primary)] h-2 rounded-full"
                        style={{ width: `${Math.min(f.importance * 500, 100)}%` }}
                      />
                    </div>
                    <span className="text-[var(--muted-foreground)] w-10 text-right">
                      {(f.importance * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </Link>
            ),
          )}
        </div>
      )}
    </div>
  );
}
