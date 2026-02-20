"""Tests for core.availability — AvailabilityFilter."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.availability import AvailabilityFilter
from core.imputation import OmicsImputer


@pytest.fixture
def af():
    return AvailabilityFilter()


class TestCheckAvailability:
    def test_returns_scores(self, af, sample_proteomics_df):
        scores = af.check_availability(sample_proteomics_df)
        assert isinstance(scores, dict)
        assert len(scores) == sample_proteomics_df.shape[1]

    def test_score_range(self, af, sample_proteomics_df):
        scores = af.check_availability(sample_proteomics_df)
        for gene, score in scores.items():
            assert 0.0 <= score <= 1.0, f"{gene} score {score} out of range"

    def test_with_no_missing(self, af):
        df = pd.DataFrame(
            np.ones((10, 5)),
            columns=[f"G{i}" for i in range(5)],
        )
        scores = af.check_availability(df)
        for score in scores.values():
            assert score == 1.0


class TestFilterGenes:
    def test_separates_available_and_filtered(self, af, sample_proteomics_df):
        available, filtered, scores = af.filter_genes(
            sample_proteomics_df, threshold=0.9
        )
        assert isinstance(available, list)
        assert isinstance(filtered, list)
        assert len(available) + len(filtered) == sample_proteomics_df.shape[1]

    def test_high_threshold_filters_more(self, af, sample_proteomics_df):
        avail_90, filt_90, _ = af.filter_genes(
            sample_proteomics_df, threshold=0.9
        )
        avail_50, filt_50, _ = af.filter_genes(
            sample_proteomics_df, threshold=0.5
        )
        assert len(avail_90) <= len(avail_50)

    def test_low_threshold_keeps_more(self, af, sample_proteomics_df):
        avail_10, _, _ = af.filter_genes(
            sample_proteomics_df, threshold=0.1
        )
        avail_99, _, _ = af.filter_genes(
            sample_proteomics_df, threshold=0.99
        )
        assert len(avail_10) >= len(avail_99)

    def test_all_available_genes(self, af):
        df = pd.DataFrame(
            np.ones((10, 5)), columns=[f"G{i}" for i in range(5)]
        )
        available, filtered, _ = af.filter_genes(df, threshold=0.9)
        assert len(available) == 5
        assert len(filtered) == 0

    def test_no_available_genes(self, af):
        df = pd.DataFrame(
            np.full((10, 5), np.nan), columns=[f"G{i}" for i in range(5)]
        )
        available, filtered, _ = af.filter_genes(df, threshold=0.9)
        assert len(available) == 0
        assert len(filtered) == 5


class TestComparePrePostImputation:
    def test_shows_rescued_genes(
        self, af, sample_proteomics_df, sample_clinical_df
    ):
        imputer = OmicsImputer()
        imputed, _ = imputer.impute(sample_proteomics_df, sample_clinical_df)
        result = af.compare_pre_post_imputation(
            sample_proteomics_df, imputed, threshold=0.9
        )
        assert "genes_rescued" in result
        assert isinstance(result["genes_rescued"], list)

    def test_keys(self, af, sample_proteomics_df, sample_clinical_df):
        imputer = OmicsImputer()
        imputed, _ = imputer.impute(sample_proteomics_df, sample_clinical_df)
        result = af.compare_pre_post_imputation(
            sample_proteomics_df, imputed, threshold=0.9
        )
        expected_keys = {
            "genes_rescued",
            "before_count",
            "after_count",
            "before_scores",
            "after_scores",
        }
        assert expected_keys == set(result.keys())
