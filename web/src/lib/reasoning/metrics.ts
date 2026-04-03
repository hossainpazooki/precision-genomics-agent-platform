/**
 * Reasoning metrics — replaces dspy_modules/metrics.py.
 * Evaluates quality of reasoning outputs without DSPy.
 */

const GENE_PATTERN = /\b([A-Z][A-Z0-9]{1,}[0-9]*)\b/g;

const STOPWORDS = new Set([
  "THE", "AND", "FOR", "NOT", "ARE", "BUT", "FROM", "WITH", "THIS",
  "THAT", "HAVE", "HAS", "HAD", "WAS", "WERE", "BEEN", "BEING",
  "WILL", "WOULD", "COULD", "SHOULD", "MAY", "MIGHT", "MUST",
  "SHALL", "CAN", "EACH", "WHICH", "THEIR", "ALL", "ANY",
  "DNA", "RNA", "QC", "MSI", "PCR", "WHO", "FDA",
]);

/**
 * Extract gene names from report text.
 */
export function extractGenesFromReport(reportText: string): string[] {
  const matches = reportText.match(GENE_PATTERN) ?? [];
  return matches.filter((g) => !STOPWORDS.has(g));
}

/**
 * Biological validity score — checks if extracted genes map to known pathways.
 * Returns a score between 0 and 1.
 */
export function biologicalValidityScore(genes: string[]): number {
  if (genes.length === 0) return 0;

  // Known MSI-associated genes (from core/constants.py)
  const knownMSIMarkers = new Set([
    "MLH1", "MSH2", "MSH6", "PMS2", "EPCAM",
    "TAP1", "TAP2", "B2M", "HLA-A", "HLA-B", "HLA-C",
    "POLD1", "POLE", "BRAF", "KRAS", "TP53",
  ]);

  const matchCount = genes.filter((g) => knownMSIMarkers.has(g)).length;
  return Math.min(matchCount / Math.max(genes.length * 0.3, 1), 1.0);
}

/**
 * Hallucination detection score — checks if referenced PubMed IDs are plausible.
 * Returns 1.0 if no PubMed IDs or all are plausible format.
 */
export function halluccinationScore(pubmedIds: string[]): number {
  if (pubmedIds.length === 0) return 1.0;

  const validFormat = pubmedIds.filter((id) => /^\d{6,10}$/.test(id.trim()));
  return validFormat.length / pubmedIds.length;
}

/**
 * Composite metric — weighted combination with hard fail on hallucination.
 */
export function compositeMetric(
  genes: string[],
  pubmedIds: string[],
): number {
  const bioScore = biologicalValidityScore(genes);
  const hallScore = halluccinationScore(pubmedIds);

  if (hallScore < 0.9) return 0;

  return 0.6 * bioScore + 0.4 * hallScore;
}
