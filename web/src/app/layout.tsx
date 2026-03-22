import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Precision Genomics Agent Platform",
  description:
    "Claude-orchestrated precision genomics platform for multi-omics biomarker discovery",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-[var(--border)] px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-semibold">
                Precision Genomics
              </h1>
              <span className="text-sm text-[var(--muted-foreground)]">
                Agent Platform
              </span>
            </div>
            <nav className="flex gap-4 text-sm">
              <a href="/" className="hover:text-[var(--primary)]">
                Dashboard
              </a>
              <a href="/analyze" className="hover:text-[var(--primary)]">
                Analyze
              </a>
              <a href="/workflows" className="hover:text-[var(--primary)]">
                Workflows
              </a>
              <a href="/biomarkers" className="hover:text-[var(--primary)]">
                Biomarkers
              </a>
            </nav>
          </header>
          <main className="flex-1 p-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
