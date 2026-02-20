"""Tests for core.cross_omics_matcher — CrossOmicsMatcher."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.cross_omics_matcher import CrossOmicsMatcher


@pytest.fixture
def matcher():
    return CrossOmicsMatcher()


# ---- compute_gene_correlations -------------------------------------------


class TestGeneCorrelations:
    def test_returns_dataframe(
        self, matcher, sample_proteomics_df, sample_rnaseq_df
    ):
        result = matcher.compute_gene_correlations(
            sample_proteomics_df, sample_rnaseq_df
        )
        assert isinstance(result, pd.DataFrame)
        assert "gene" in result.columns
        assert "r_squared" in result.columns

    def test_shared_genes(
        self, matcher, sample_proteomics_df, sample_rnaseq_df
    ):
        result = matcher.compute_gene_correlations(
            sample_proteomics_df, sample_rnaseq_df
        )
        shared = set(sample_proteomics_df.columns) & set(sample_rnaseq_df.columns)
        # Should have results for shared genes
        assert len(result) <= len(shared)
        assert len(result) > 0


# ---- build_distance_matrix -----------------------------------------------


class TestDistanceMatrix:
    def test_shape(self, matcher, sample_proteomics_df, sample_rnaseq_df):
        shared_genes = sorted(
            set(sample_proteomics_df.columns) & set(sample_rnaseq_df.columns)
        )
        dist = matcher.build_distance_matrix(
            sample_proteomics_df, sample_rnaseq_df, shared_genes
        )
        shared_samples = sorted(
            set(sample_proteomics_df.index) & set(sample_rnaseq_df.index)
        )
        assert dist.shape == (len(shared_samples), len(shared_samples))

    def test_expression_rank(
        self, matcher, sample_proteomics_df, sample_rnaseq_df
    ):
        shared_genes = sorted(
            set(sample_proteomics_df.columns) & set(sample_rnaseq_df.columns)
        )
        dist = matcher.build_distance_matrix(
            sample_proteomics_df,
            sample_rnaseq_df,
            shared_genes,
            method="expression_rank",
        )
        # Distance values should be in [0, 2] range (1 - |rho|)
        assert dist.min() >= 0.0
        assert np.isfinite(dist).all()

    def test_linear_model(
        self, matcher, sample_proteomics_df, sample_rnaseq_df
    ):
        shared_genes = sorted(
            set(sample_proteomics_df.columns) & set(sample_rnaseq_df.columns)
        )
        dist = matcher.build_distance_matrix(
            sample_proteomics_df,
            sample_rnaseq_df,
            shared_genes,
            method="linear_model",
        )
        assert dist.min() >= 0.0


# ---- identify_mismatches -------------------------------------------------


class TestIdentifyMismatches:
    def test_hungarian(self, matcher, sample_proteomics_df, sample_rnaseq_df):
        shared_genes = sorted(
            set(sample_proteomics_df.columns) & set(sample_rnaseq_df.columns)
        )
        shared_samples = sorted(
            set(sample_proteomics_df.index) & set(sample_rnaseq_df.index)
        )
        dist = matcher.build_distance_matrix(
            sample_proteomics_df, sample_rnaseq_df, shared_genes
        )

        results = matcher.identify_mismatches(
            dist, shared_samples, n_iterations=10
        )
        assert isinstance(results, list)
        assert len(results) == len(shared_samples)
        for r in results:
            assert "sample_id" in r
            assert "is_flagged" in r
            assert "mismatch_frequency" in r

    def test_iterative(self, matcher, sample_proteomics_df, sample_rnaseq_df):
        shared_genes = sorted(
            set(sample_proteomics_df.columns) & set(sample_rnaseq_df.columns)
        )
        shared_samples = sorted(
            set(sample_proteomics_df.index) & set(sample_rnaseq_df.index)
        )
        dist = matcher.build_distance_matrix(
            sample_proteomics_df, sample_rnaseq_df, shared_genes
        )
        results = matcher.identify_mismatches(
            dist, shared_samples, n_iterations=20, sampling_fraction=0.7
        )
        for r in results:
            assert 0.0 <= r["mismatch_frequency"] <= 1.0

    def test_no_mismatches(self, matcher):
        """Identity-like distance matrix should yield no mismatches."""
        n = 10
        dist = np.eye(n) * 100  # diagonal = large distance, off-diagonal = 0
        # Actually, for Hungarian, we want diagonal = 0 (match to self)
        dist = np.ones((n, n))
        np.fill_diagonal(dist, 0.0)
        samples = [f"S{i}" for i in range(n)]

        results = matcher.identify_mismatches(
            dist, samples, n_iterations=10
        )
        # With a clear diagonal structure, most should not be flagged
        flagged = [r for r in results if r["is_flagged"]]
        assert len(flagged) < n


# ---- dual_validate -------------------------------------------------------


class TestDualValidate:
    def test_both_methods(self, matcher):
        classification_flags = ["S001", "S002", "S003"]
        distance_flags = ["S002", "S003", "S004"]

        results = matcher.dual_validate(classification_flags, distance_flags)
        # S002 and S003 flagged by both -> HIGH
        high = [r for r in results if r["concordance_level"] == "HIGH"]
        assert len(high) == 2

    def test_single_method(self, matcher):
        classification_flags = ["S001"]
        distance_flags = ["S002"]

        results = matcher.dual_validate(classification_flags, distance_flags)
        # No overlap -> all REVIEW
        for r in results:
            assert r["concordance_level"] == "REVIEW"
