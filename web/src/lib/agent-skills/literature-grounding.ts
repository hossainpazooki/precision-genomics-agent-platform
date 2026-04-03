/**
 * Agent skill: Literature grounding for biomarker genes.
 * Migrated from agent_skills/literature_grounding.py.
 *
 * Queries PubMed E-utilities API and optionally synthesizes with Claude.
 */

import Anthropic from "@anthropic-ai/sdk";

const PUBMED_ESEARCH_URL =
  "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi";

interface LiteratureResult {
  query: string;
  pmid_count: number;
  top_pmids: string[];
  source: string;
  error?: string;
}

interface SynthesisResult {
  gene: string;
  context: string;
  confidence: "high" | "medium" | "low";
  summary: string;
  source: string;
}

async function pubmedSearch(
  gene: string,
  context: string,
): Promise<LiteratureResult> {
  const query = `${gene} AND ${context}`;
  try {
    const url = new URL(PUBMED_ESEARCH_URL);
    url.searchParams.set("db", "pubmed");
    url.searchParams.set("term", query);
    url.searchParams.set("retmax", "5");
    url.searchParams.set("retmode", "json");

    const res = await fetch(url.toString());
    const data = await res.json();
    const result = data.esearchresult ?? {};
    return {
      query,
      pmid_count: parseInt(result.count ?? "0", 10),
      top_pmids: result.idlist ?? [],
      source: "pubmed",
    };
  } catch (err) {
    return {
      query,
      pmid_count: 0,
      top_pmids: [],
      source: "error",
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

async function synthesize(
  gene: string,
  context: string,
  literature: LiteratureResult,
  useLLM: boolean,
): Promise<SynthesisResult> {
  const pmidCount = literature.pmid_count;

  if (!useLLM) {
    let confidence: "high" | "medium" | "low";
    if (pmidCount >= 10) confidence = "high";
    else if (pmidCount >= 3) confidence = "medium";
    else confidence = "low";

    return {
      gene,
      context,
      confidence,
      summary: `${gene} has ${pmidCount} PubMed references in ${context} context.`,
      source: "heuristic",
    };
  }

  try {
    const client = new Anthropic();
    const message = await client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 300,
      messages: [
        {
          role: "user",
          content: `Summarise the role of ${gene} in ${context} based on ${pmidCount} PubMed references. Classify confidence as high/medium/low.`,
        },
      ],
    });
    const text =
      message.content[0].type === "text" ? message.content[0].text : "";
    return {
      gene,
      context,
      confidence: "medium",
      summary: text,
      source: "llm",
    };
  } catch {
    return {
      gene,
      context,
      confidence: "low",
      summary: `LLM synthesis failed for ${gene}`,
      source: "error",
    };
  }
}

export async function runLiteratureGrounding(
  genes: string[],
  context: string = "MSI",
  useLLM: boolean = false,
): Promise<Record<string, unknown>> {
  const results: Array<Record<string, unknown>> = [];

  for (const gene of genes) {
    const literature = await pubmedSearch(gene, context);
    const synthesis = await synthesize(gene, context, literature, useLLM);
    results.push({ gene, literature, synthesis });
  }

  const confidences = results.map(
    (r) => (r.synthesis as SynthesisResult).confidence,
  );
  const highCount = confidences.filter((c) => c === "high").length;
  const medCount = confidences.filter((c) => c === "medium").length;
  const total = confidences.length;

  let overall: string;
  if (total === 0) overall = "none";
  else if (highCount / total >= 0.5) overall = "high";
  else if ((highCount + medCount) / total >= 0.5) overall = "medium";
  else overall = "low";

  return {
    genes_queried: genes,
    context,
    results,
    overall_confidence: overall,
    n_genes: genes.length,
    n_high_confidence: highCount,
    n_medium_confidence: medCount,
    n_low_confidence: total - highCount - medCount,
  };
}
