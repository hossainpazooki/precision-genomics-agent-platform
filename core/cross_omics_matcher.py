"""Cross-omics sample matching via proteomics-RNAseq concordance.

Detects sample mismatches by comparing proteomics and RNA-Seq profiles
using distance matrices and the Hungarian algorithm.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

try:
    from scipy.optimize import linear_sum_assignment
    from scipy.stats import spearmanr
    from sklearn.linear_model import LinearRegression
except ImportError:
    linear_sum_assignment = None  # type: ignore[assignment]
    spearmanr = None  # type: ignore[assignment]
    LinearRegression = None  # type: ignore[assignment]


class CrossOmicsMatcher:
    """Match samples across proteomics and RNA-Seq modalities."""

    def compute_gene_correlations(
        self,
        proteomics_df: pd.DataFrame,
        rnaseq_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Per-gene linear regression (protein ~ RNA) for shared genes.

        Returns
        -------
        pd.DataFrame
            Columns: gene, r_squared, slope, intercept. One row per shared gene.
        """
        if LinearRegression is None:
            raise ImportError("scikit-learn is required for gene correlations")

        shared_genes = sorted(set(proteomics_df.columns) & set(rnaseq_df.columns))
        shared_samples = sorted(set(proteomics_df.index) & set(rnaseq_df.index))

        if not shared_genes or not shared_samples:
            return pd.DataFrame(columns=["gene", "r_squared", "slope", "intercept"])

        records = []
        for gene in shared_genes:
            prot = proteomics_df.loc[shared_samples, gene]
            rna = rnaseq_df.loc[shared_samples, gene]

            # Drop pairs with NaN
            valid = prot.notna() & rna.notna()
            if valid.sum() < 3:
                records.append(
                    {
                        "gene": gene,
                        "r_squared": 0.0,
                        "slope": 0.0,
                        "intercept": 0.0,
                    }
                )
                continue

            X = rna[valid].values.reshape(-1, 1)
            y = prot[valid].values

            model = LinearRegression()
            model.fit(X, y)
            r2 = model.score(X, y)

            records.append(
                {
                    "gene": gene,
                    "r_squared": float(r2),
                    "slope": float(model.coef_[0]),
                    "intercept": float(model.intercept_),
                }
            )

        return pd.DataFrame(records)

    def build_distance_matrix(
        self,
        proteomics_df: pd.DataFrame,
        rnaseq_df: pd.DataFrame,
        gene_set: list[str],
        method: str = "expression_rank",
    ) -> np.ndarray:
        """Build NxN distance matrix between samples across omics.

        Parameters
        ----------
        method : str
            ``"expression_rank"``: 1 - Spearman rank correlation.
            ``"linear_model"``: mean squared residual from per-gene regression.

        Returns
        -------
        np.ndarray
            N x N distance matrix where entry (i, j) is the distance between
            proteomics sample i and RNA-Seq sample j.
        """
        shared_samples = sorted(set(proteomics_df.index) & set(rnaseq_df.index))
        genes = [g for g in gene_set if g in proteomics_df.columns and g in rnaseq_df.columns]

        if not genes:
            genes = sorted(set(proteomics_df.columns) & set(rnaseq_df.columns))

        n = len(shared_samples)
        dist = np.zeros((n, n))

        prot = proteomics_df.loc[shared_samples, genes].fillna(0.0).values
        rna = rnaseq_df.loc[shared_samples, genes].fillna(0.0).values

        if method == "linear_model":
            dist = self._distance_linear_model(prot, rna)
        else:
            dist = self._distance_expression_rank(prot, rna)

        return dist

    def _distance_expression_rank(self, prot: np.ndarray, rna: np.ndarray) -> np.ndarray:
        """Rank-correlation-based distance: 1 - |spearman_rho|."""
        n = prot.shape[0]
        dist = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    if spearmanr is not None:
                        rho, _ = spearmanr(prot[i], rna[j])
                        if np.isnan(rho):
                            rho = 0.0
                    else:
                        rho = 0.0
                dist[i, j] = 1.0 - abs(rho)

        return dist

    def _distance_linear_model(self, prot: np.ndarray, rna: np.ndarray) -> np.ndarray:
        """Residual-based distance from per-sample regression."""
        n = prot.shape[0]
        dist = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                residuals = prot[i] - rna[j]
                dist[i, j] = float(np.mean(residuals**2))

        return dist

    def identify_mismatches(
        self,
        distance_matrix: np.ndarray,
        sample_ids: list[str],
        method: str = "hungarian",
        n_iterations: int = 100,
        sampling_fraction: float = 0.8,
    ) -> list[dict]:
        """Identify sample mismatches using optimal assignment.

        Uses the Hungarian algorithm with iterative random subsampling
        and majority voting.

        Returns
        -------
        list[dict]
            Each dict: sample_id, expected_match, mismatch_frequency, is_flagged.
        """
        if linear_sum_assignment is None:
            raise ImportError("scipy is required for Hungarian matching")

        n = len(sample_ids)
        mismatch_counts = np.zeros(n, dtype=int)
        rng = np.random.RandomState(42)

        for _ in range(n_iterations):
            # Random subsample of genes (columns in the original data)
            # Here we subsample samples to create variability
            n_sub = max(2, int(n * sampling_fraction))
            indices = sorted(rng.choice(n, size=n_sub, replace=False))

            sub_matrix = distance_matrix[np.ix_(indices, indices)]

            row_ind, col_ind = linear_sum_assignment(sub_matrix)

            for _idx_in_sub, (ri, ci) in enumerate(zip(row_ind, col_ind, strict=False)):
                original_idx = indices[ri]
                matched_idx = indices[ci]
                if original_idx != matched_idx:
                    mismatch_counts[original_idx] += 1

        results = []
        for i in range(n):
            freq = mismatch_counts[i] / n_iterations
            results.append(
                {
                    "sample_id": sample_ids[i],
                    "expected_match": sample_ids[i],
                    "mismatch_frequency": float(freq),
                    "is_flagged": freq > 0.5,
                }
            )

        return results

    def dual_validate(
        self,
        classification_flags: list[str],
        distance_flags: list[str],
    ) -> list[dict]:
        """Cross-validate mismatch flags from two methods.

        Both methods flagged = HIGH confidence.
        Single method flagged = REVIEW.
        Neither = PASS.

        Returns
        -------
        list[dict]
            Each dict: sample_id, concordance_level, flagged_by.
        """
        all_samples = sorted(set(classification_flags) | set(distance_flags))
        classification_set = set(classification_flags)
        distance_set = set(distance_flags)

        results = []
        for sample in all_samples:
            in_class = sample in classification_set
            in_dist = sample in distance_set

            if in_class and in_dist:
                level = "HIGH"
                flagged_by = ["classification", "distance"]
            elif in_class:
                level = "REVIEW"
                flagged_by = ["classification"]
            else:
                level = "REVIEW"
                flagged_by = ["distance"]

            results.append(
                {
                    "sample_id": sample,
                    "concordance_level": level,
                    "flagged_by": flagged_by,
                }
            )

        return results
