"""Gene availability filtering for multi-omics expression data.

Filters genes based on non-missing data availability thresholds and
compares pre/post-imputation availability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


class AvailabilityFilter:
    """Filter genes by data availability (fraction of non-missing samples)."""

    def check_availability(
        self,
        expression_matrix: pd.DataFrame,
        threshold: float = 0.9,
    ) -> dict[str, float]:
        """Compute availability score (fraction non-missing) for every gene.

        Parameters
        ----------
        expression_matrix : pd.DataFrame
            Samples x genes expression matrix.
        threshold : float
            Not used for computation, included for API consistency.

        Returns
        -------
        dict[str, float]
            Mapping of gene name to availability score in [0, 1].
        """
        n_samples = len(expression_matrix)
        if n_samples == 0:
            return {}

        non_missing_counts = expression_matrix.notna().sum()
        scores = (non_missing_counts / n_samples).to_dict()
        return scores

    def filter_genes(
        self,
        expression_matrix: pd.DataFrame,
        threshold: float = 0.9,
        use_imputed: bool = True,
    ) -> tuple[list[str], list[str], dict[str, float]]:
        """Split genes into available and filtered based on threshold.

        Parameters
        ----------
        expression_matrix : pd.DataFrame
            Samples x genes expression matrix.
        threshold : float
            Minimum fraction of non-missing samples required.
        use_imputed : bool
            If True, considers imputed (non-NaN) values as available.

        Returns
        -------
        available_genes : list[str]
            Genes meeting the threshold.
        filtered_genes : list[str]
            Genes below the threshold.
        availability_scores : dict[str, float]
            All gene availability scores.
        """
        scores = self.check_availability(expression_matrix, threshold)

        available_genes = [gene for gene, score in scores.items() if score >= threshold]
        filtered_genes = [gene for gene, score in scores.items() if score < threshold]

        return available_genes, filtered_genes, scores

    def compare_pre_post_imputation(
        self,
        original_matrix: pd.DataFrame,
        imputed_matrix: pd.DataFrame,
        threshold: float = 0.9,
    ) -> dict:
        """Compare gene availability before and after imputation.

        Returns
        -------
        dict
            Keys: genes_rescued (list), before_count (int), after_count (int),
            before_scores (dict), after_scores (dict).
        """
        before_available, before_filtered, before_scores = self.filter_genes(original_matrix, threshold)
        after_available, after_filtered, after_scores = self.filter_genes(imputed_matrix, threshold)

        # Genes that were below threshold before but above after imputation
        before_set = set(before_available)
        after_set = set(after_available)
        genes_rescued = sorted(after_set - before_set)

        return {
            "genes_rescued": genes_rescued,
            "before_count": len(before_available),
            "after_count": len(after_available),
            "before_scores": before_scores,
            "after_scores": after_scores,
        }
