"""Tests for core.imputation — OmicsImputer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.constants import Y_CHROMOSOME_GENES
from core.imputation import OmicsImputer


@pytest.fixture
def imputer():
    return OmicsImputer()


# ---- classify_missingness ------------------------------------------------


class TestClassifyMissingness:
    def test_marks_y_chr_female_as_mnar(
        self, imputer, sample_proteomics_df, sample_clinical_df
    ):
        mnar_mask, _ = imputer.classify_missingness(
            sample_proteomics_df, sample_clinical_df
        )
        # Female samples should have MNAR for Y-chr genes that are NaN
        clinical = sample_clinical_df.set_index("sample_id")
        female_samples = clinical[clinical["gender"] == "Female"].index
        y_genes = [g for g in Y_CHROMOSOME_GENES if g in sample_proteomics_df.columns]

        for sample in female_samples:
            if sample in mnar_mask.index:
                for gene in y_genes:
                    if pd.isna(sample_proteomics_df.loc[sample, gene]):
                        assert mnar_mask.loc[sample, gene], (
                            f"Expected MNAR at {sample}, {gene}"
                        )

    def test_marks_random_nan_as_mar(
        self, imputer, sample_proteomics_df, sample_clinical_df
    ):
        _, mar_mask = imputer.classify_missingness(
            sample_proteomics_df, sample_clinical_df
        )
        # MAR mask should flag non-Y-chr NaN in male samples
        clinical = sample_clinical_df.set_index("sample_id")
        male_samples = clinical[clinical["gender"] == "Male"].index
        non_y_genes = [
            g for g in sample_proteomics_df.columns if g not in Y_CHROMOSOME_GENES
        ]

        for sample in male_samples:
            if sample in mar_mask.index:
                for gene in non_y_genes:
                    if pd.isna(sample_proteomics_df.loc[sample, gene]):
                        assert mar_mask.loc[sample, gene]

    def test_no_y_chr_genes(self, imputer, sample_clinical_df):
        """When matrix has no Y-chr genes, no MNAR should be detected."""
        df = pd.DataFrame(
            np.random.rand(5, 3),
            index=[f"S{i}" for i in range(1, 6)],
            columns=["BRCA1", "TP53", "EGFR"],
        )
        df.iloc[0, 0] = np.nan
        mnar_mask, mar_mask = imputer.classify_missingness(df, sample_clinical_df)
        assert mnar_mask.sum().sum() == 0
        assert mar_mask.sum().sum() == 1


# ---- impute_nmf ----------------------------------------------------------


class TestImputeNMF:
    def test_fills_missing_values(self, imputer, sample_proteomics_df):
        result = imputer.impute_nmf(sample_proteomics_df, n_components=2)
        assert result.isna().sum().sum() < sample_proteomics_df.isna().sum().sum()

    def test_auto_k_selection(self, imputer, sample_proteomics_df):
        result = imputer.impute_nmf(sample_proteomics_df, n_components="auto")
        assert result.isna().sum().sum() < sample_proteomics_df.isna().sum().sum()

    def test_preserves_non_missing(self, imputer, sample_proteomics_df):
        known_mask = sample_proteomics_df.notna()
        result = imputer.impute_nmf(sample_proteomics_df, n_components=2)
        # Non-missing values should remain unchanged
        orig = sample_proteomics_df[known_mask]
        filled = result[known_mask]
        np.testing.assert_array_almost_equal(
            orig.values[~np.isnan(orig.values)],
            filled.values[~np.isnan(orig.values)],
            decimal=3,
        )

    def test_result_non_negative(self, imputer, sample_proteomics_df):
        result = imputer.impute_nmf(sample_proteomics_df, n_components=2)
        assert (result.fillna(0) >= 0).all().all()


# ---- impute (full pipeline) ---------------------------------------------


class TestImputeFullPipeline:
    def test_returns_filled_matrix(
        self, imputer, sample_proteomics_df, sample_clinical_df
    ):
        filled, _ = imputer.impute(sample_proteomics_df, sample_clinical_df)
        assert filled.isna().sum().sum() == 0

    def test_returns_stats(
        self, imputer, sample_proteomics_df, sample_clinical_df
    ):
        _, stats = imputer.impute(sample_proteomics_df, sample_clinical_df)
        assert isinstance(stats, dict)
        assert stats["total_missing"] > 0

    def test_mnar_positions_get_zero(
        self, imputer, sample_proteomics_df, sample_clinical_df
    ):
        mnar_mask, _ = imputer.classify_missingness(
            sample_proteomics_df, sample_clinical_df
        )
        filled, _ = imputer.impute(sample_proteomics_df, sample_clinical_df)
        # MNAR positions should be zero-filled
        if mnar_mask.any().any():
            mnar_values = filled[mnar_mask]
            assert (mnar_values.fillna(0) == 0).all().all()

    def test_preserves_shape(
        self, imputer, sample_proteomics_df, sample_clinical_df
    ):
        filled, _ = imputer.impute(sample_proteomics_df, sample_clinical_df)
        assert filled.shape == sample_proteomics_df.shape

    def test_stats_keys(
        self, imputer, sample_proteomics_df, sample_clinical_df
    ):
        _, stats = imputer.impute(sample_proteomics_df, sample_clinical_df)
        expected_keys = {"total_missing", "n_mnar", "n_mar", "remaining_nan"}
        assert expected_keys.issubset(set(stats.keys()))

    def test_no_missing_values(self, imputer, sample_clinical_df):
        """When there are no missing values, output equals input."""
        df = pd.DataFrame(
            np.random.rand(5, 3),
            index=[f"S{i}" for i in range(1, 6)],
            columns=["BRCA1", "TP53", "EGFR"],
        )
        filled, stats = imputer.impute(df, sample_clinical_df)
        assert stats["total_missing"] == 0
        pd.testing.assert_frame_equal(filled, df)

    def test_empty_matrix_edge_case(self, imputer, sample_clinical_df):
        """Empty matrix should not raise."""
        df = pd.DataFrame()
        filled, stats = imputer.impute(df, sample_clinical_df)
        assert stats["total_missing"] == 0

    def test_all_missing_column(self, imputer, sample_clinical_df):
        """A column that is entirely NaN should still be handled."""
        df = pd.DataFrame(
            {
                "BRCA1": [1.0, 2.0, 3.0],
                "ALL_NAN": [np.nan, np.nan, np.nan],
            },
            index=["S001", "S002", "S003"],
        )
        filled, stats = imputer.impute(df, sample_clinical_df)
        assert filled.isna().sum().sum() == 0
