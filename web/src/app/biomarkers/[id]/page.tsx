"use client";

import { useParams } from "next/navigation";
import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function BiomarkerDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const { data, error, isLoading } = useSWR(
    `/api/biomarkers/${id}/features`,
    fetcher,
  );

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-[var(--muted-foreground)]">
        Loading panel...
      </div>
    );
  }

  if (error || !data || data.error) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-red-600">
        Panel not found
      </div>
    );
  }

  const features = (data.features as Array<{ gene: string; importance: number }>) ?? [];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Panel #{data.panel_id}</h2>
        <p className="text-sm text-[var(--muted-foreground)] mt-1">
          Target: {data.target} | Modality: {data.modality} |{" "}
          {data.n_features} features
        </p>
      </div>

      {/* Feature Importance Chart */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Feature Importance</h3>
        <div className="space-y-2">
          {features.map((f) => (
            <div key={f.gene} className="flex items-center gap-3">
              <span className="font-mono text-sm w-20 text-right">
                {f.gene}
              </span>
              <div className="flex-1 bg-[var(--muted)] rounded-full h-4">
                <div
                  className="bg-[var(--primary)] h-4 rounded-full flex items-center justify-end pr-2"
                  style={{
                    width: `${Math.max(f.importance * 500, 5)}%`,
                    maxWidth: "100%",
                  }}
                >
                  {f.importance > 0.05 && (
                    <span className="text-[10px] text-white">
                      {(f.importance * 100).toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
              <span className="text-xs text-[var(--muted-foreground)] w-14 text-right">
                {(f.importance * 100).toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Feature Table */}
      <div>
        <h3 className="text-lg font-semibold mb-3">All Features</h3>
        <div className="rounded-lg border border-[var(--border)] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[var(--muted)]">
              <tr>
                <th className="text-left p-3">#</th>
                <th className="text-left p-3">Gene</th>
                <th className="text-left p-3">Importance</th>
              </tr>
            </thead>
            <tbody>
              {features.map((f, i) => (
                <tr
                  key={f.gene}
                  className="border-t border-[var(--border)]"
                >
                  <td className="p-3 text-[var(--muted-foreground)]">
                    {i + 1}
                  </td>
                  <td className="p-3 font-mono">{f.gene}</td>
                  <td className="p-3">{(f.importance * 100).toFixed(3)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
