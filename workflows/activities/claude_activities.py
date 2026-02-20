"""Claude API activities for biological interpretation."""

from __future__ import annotations

try:
    from temporalio import activity

    HAS_TEMPORAL = True
except ImportError:
    HAS_TEMPORAL = False

if HAS_TEMPORAL:

    @activity.defn
    async def generate_interpretation_activity(
        genes: list[str], target: str
    ) -> dict:
        """Call Anthropic API to generate biological interpretation of gene panel.

        Uses RetryPolicy with 3 retries and exponential backoff (configured at
        workflow level). Falls back to a template response if the API is unavailable.
        """
        try:
            import anthropic

            from core.config import get_settings

            settings = get_settings()
            if not settings.anthropic_api_key:
                return _fallback_interpretation(genes, target)

            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

            gene_list = ", ".join(genes[:20])
            prompt = (
                f"You are a molecular biology expert. Provide a concise biological "
                f"interpretation of the following gene panel discovered as biomarkers "
                f"for {target} status prediction:\n\n"
                f"Genes: {gene_list}\n\n"
                f"Cover: (1) known pathway associations, (2) biological significance "
                f"for {target}, (3) potential clinical relevance."
            )

            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            interpretation_text = response.content[0].text

            return {
                "interpretation": interpretation_text,
                "genes_analyzed": genes,
                "target": target,
                "model": "claude-sonnet-4-20250514",
                "source": "anthropic_api",
            }

        except ImportError:
            return _fallback_interpretation(genes, target)
        except Exception as exc:
            activity.logger.warning("Claude API call failed: %s", str(exc))
            return _fallback_interpretation(genes, target)

    @activity.defn
    async def compile_report_activity(results: dict) -> dict:
        """Compile all analysis results into a structured report."""
        report: dict = {
            "summary": {},
            "feature_panel": {},
            "classification": {},
            "cross_omics_validation": {},
            "interpretation": {},
        }

        if "data_summary" in results:
            report["summary"]["data"] = results["data_summary"]

        if "integrated" in results:
            integrated = results["integrated"]
            report["feature_panel"] = {
                "features": integrated.get("features", []),
                "n_features": integrated.get("n_total", 0),
                "modalities": integrated.get("modalities", []),
            }

        if "classification" in results:
            report["classification"] = results["classification"]

        if "interpretation" in results:
            report["interpretation"] = results["interpretation"]

        if "cross_validation" in results:
            report["cross_omics_validation"] = results["cross_validation"]

        if "feature_panels" in results:
            panels = results["feature_panels"]
            overlap_genes: set[str] = set()
            if len(panels) >= 2:
                sets = [set(p.get("features", [])) for p in panels]
                overlap_genes = sets[0]
                for s in sets[1:]:
                    overlap_genes = overlap_genes & s
            report["cross_omics_validation"]["overlapping_genes"] = list(overlap_genes)
            report["cross_omics_validation"]["n_overlapping"] = len(overlap_genes)

        return report


def _fallback_interpretation(genes: list[str], target: str) -> dict:
    """Provide a template interpretation when the API is unavailable."""
    return {
        "interpretation": (
            f"Gene panel of {len(genes)} features identified for {target} prediction. "
            f"Key genes include: {', '.join(genes[:5])}. "
            f"Biological interpretation requires manual review."
        ),
        "genes_analyzed": genes,
        "target": target,
        "model": "fallback",
        "source": "template",
    }
