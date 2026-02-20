"""Agent skill: Literature grounding for biomarker genes.

Queries PubMed E-utilities API (or mocks the query in test mode) and
optionally synthesises findings with Claude for confidence classification.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class LiteratureGroundingSkill:
    """Ground biomarker genes in published literature via PubMed."""

    def __init__(self, http_client=None, llm_client=None) -> None:
        self.http_client = http_client
        self.llm_client = llm_client

    async def _pubmed_search(self, gene: str, context: str) -> dict:
        """Search PubMed for a gene in a given context.

        Returns a dict with ``pmid_count``, ``top_pmids``, and ``query``.
        """
        query = f"{gene} AND {context}"
        if self.http_client is None:
            return {
                "query": query,
                "pmid_count": 0,
                "top_pmids": [],
                "source": "mock",
            }

        try:
            response = await self.http_client.get(
                PUBMED_ESEARCH_URL,
                params={
                    "db": "pubmed",
                    "term": query,
                    "retmax": 5,
                    "retmode": "json",
                },
            )
            data = response.json()
            result = data.get("esearchresult", {})
            return {
                "query": query,
                "pmid_count": int(result.get("count", 0)),
                "top_pmids": result.get("idlist", []),
                "source": "pubmed",
            }
        except Exception as exc:
            logger.warning("PubMed search failed for %s: %s", gene, exc)
            return {
                "query": query,
                "pmid_count": 0,
                "top_pmids": [],
                "source": "error",
                "error": str(exc),
            }

    async def _synthesize(self, gene: str, context: str, literature: dict) -> dict:
        """Use an LLM client to synthesise literature findings."""
        if self.llm_client is None:
            pmid_count = literature.get("pmid_count", 0)
            if pmid_count >= 10:
                confidence = "high"
            elif pmid_count >= 3:
                confidence = "medium"
            else:
                confidence = "low"
            return {
                "gene": gene,
                "context": context,
                "confidence": confidence,
                "summary": f"{gene} has {pmid_count} PubMed references in {context} context.",
                "source": "heuristic",
            }

        try:
            prompt = (
                f"Summarise the role of {gene} in {context} based on "
                f"{literature.get('pmid_count', 0)} PubMed references. "
                f"Classify confidence as high/medium/low."
            )
            response = await self.llm_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            return {
                "gene": gene,
                "context": context,
                "summary": text,
                "confidence": "medium",
                "source": "llm",
            }
        except Exception as exc:
            logger.warning("LLM synthesis failed for %s: %s", gene, exc)
            return {
                "gene": gene,
                "context": context,
                "confidence": "low",
                "summary": f"LLM synthesis failed: {exc}",
                "source": "error",
            }

    async def run(
        self,
        genes: list[str],
        context: str = "MSI",
    ) -> dict:
        """Query PubMed for each gene, synthesise, and return grounding report."""
        results: list[dict[str, Any]] = []

        for gene in genes:
            literature = await self._pubmed_search(gene, context)
            synthesis = await self._synthesize(gene, context, literature)
            results.append(
                {
                    "gene": gene,
                    "literature": literature,
                    "synthesis": synthesis,
                }
            )

        # Aggregate confidence
        confidences = [r["synthesis"]["confidence"] for r in results]
        high_count = confidences.count("high")
        med_count = confidences.count("medium")
        total = len(confidences)

        if total == 0:
            overall = "none"
        elif high_count / total >= 0.5:
            overall = "high"
        elif (high_count + med_count) / total >= 0.5:
            overall = "medium"
        else:
            overall = "low"

        return {
            "genes_queried": genes,
            "context": context,
            "results": results,
            "overall_confidence": overall,
            "n_genes": len(genes),
            "n_high_confidence": high_count,
            "n_medium_confidence": med_count,
            "n_low_confidence": total - high_count - med_count,
        }
