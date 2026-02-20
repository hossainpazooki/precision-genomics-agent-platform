"""Tests for core.pipeline — COSMOInspiredPipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.pipeline import COSMOInspiredPipeline


@pytest.fixture
def pipeline():
    return COSMOInspiredPipeline()


# ---- Full pipeline run (with in-memory data) ----------------------------


class TestPipelineRun:
    def test_run_returns_results(
        self,
        pipeline,
        sample_clinical_df,
        sample_proteomics_df,
        sample_rnaseq_df,
        sample_msi_labels,
        sample_gender_labels,
        sample_mismatch_labels,
    ):
        results = pipeline.run(
            clinical_df=sample_clinical_df,
            proteomics_df=sample_proteomics_df,
            rnaseq_df=sample_rnaseq_df,
            msi_labels=sample_msi_labels,
            gender_labels=sample_gender_labels,
            mismatch_labels=sample_mismatch_labels,
        )
        assert isinstance(results, dict)
        assert "stages" in results

    def test_result_keys(
        self,
        pipeline,
        sample_clinical_df,
        sample_proteomics_df,
        sample_rnaseq_df,
        sample_msi_labels,
        sample_gender_labels,
        sample_mismatch_labels,
    ):
        results = pipeline.run(
            clinical_df=sample_clinical_df,
            proteomics_df=sample_proteomics_df,
            rnaseq_df=sample_rnaseq_df,
            msi_labels=sample_msi_labels,
            gender_labels=sample_gender_labels,
            mismatch_labels=sample_mismatch_labels,
        )
        stages = results["stages"]
        assert "impute" in stages
        assert "match" in stages
        assert "predict" in stages
        assert "correct" in stages

    def test_stage_1_imputation(
        self,
        pipeline,
        sample_clinical_df,
        sample_proteomics_df,
        sample_rnaseq_df,
        sample_msi_labels,
        sample_gender_labels,
        sample_mismatch_labels,
    ):
        results = pipeline.run(
            clinical_df=sample_clinical_df,
            proteomics_df=sample_proteomics_df,
            rnaseq_df=sample_rnaseq_df,
            msi_labels=sample_msi_labels,
            gender_labels=sample_gender_labels,
            mismatch_labels=sample_mismatch_labels,
        )
        impute = results["stages"]["impute"]
        assert "imputed_proteomics" in impute
        assert "imputed_rnaseq" in impute
        # Imputed matrices should have no NaN
        assert impute["imputed_proteomics"].isna().sum().sum() == 0
        assert impute["imputed_rnaseq"].isna().sum().sum() == 0

    def test_stage_2_matching(
        self,
        pipeline,
        sample_clinical_df,
        sample_proteomics_df,
        sample_rnaseq_df,
        sample_msi_labels,
        sample_gender_labels,
        sample_mismatch_labels,
    ):
        results = pipeline.run(
            clinical_df=sample_clinical_df,
            proteomics_df=sample_proteomics_df,
            rnaseq_df=sample_rnaseq_df,
            msi_labels=sample_msi_labels,
            gender_labels=sample_gender_labels,
            mismatch_labels=sample_mismatch_labels,
        )
        match = results["stages"]["match"]
        assert "mismatches" in match

    def test_stage_3_classification(
        self,
        pipeline,
        sample_clinical_df,
        sample_proteomics_df,
        sample_rnaseq_df,
        sample_msi_labels,
        sample_gender_labels,
        sample_mismatch_labels,
    ):
        results = pipeline.run(
            clinical_df=sample_clinical_df,
            proteomics_df=sample_proteomics_df,
            rnaseq_df=sample_rnaseq_df,
            msi_labels=sample_msi_labels,
            gender_labels=sample_gender_labels,
            mismatch_labels=sample_mismatch_labels,
        )
        predict = results["stages"]["predict"]
        assert "flagged_samples" in predict

    def test_stage_4_correction(
        self,
        pipeline,
        sample_clinical_df,
        sample_proteomics_df,
        sample_rnaseq_df,
        sample_msi_labels,
        sample_gender_labels,
        sample_mismatch_labels,
    ):
        results = pipeline.run(
            clinical_df=sample_clinical_df,
            proteomics_df=sample_proteomics_df,
            rnaseq_df=sample_rnaseq_df,
            msi_labels=sample_msi_labels,
            gender_labels=sample_gender_labels,
            mismatch_labels=sample_mismatch_labels,
        )
        correct = results["stages"]["correct"]
        assert "validations" in correct
        assert "n_high_confidence" in correct
        assert "n_review" in correct


class TestPipelineConfig:
    def test_with_custom_config(
        self,
        sample_clinical_df,
        sample_proteomics_df,
        sample_rnaseq_df,
        sample_msi_labels,
        sample_gender_labels,
        sample_mismatch_labels,
    ):
        config = {"random_state": 123, "n_iterations": 5}
        pipeline = COSMOInspiredPipeline(config=config)
        results = pipeline.run(
            clinical_df=sample_clinical_df,
            proteomics_df=sample_proteomics_df,
            rnaseq_df=sample_rnaseq_df,
            msi_labels=sample_msi_labels,
            gender_labels=sample_gender_labels,
            mismatch_labels=sample_mismatch_labels,
        )
        assert isinstance(results, dict)

    def test_stages_sequential(
        self,
        pipeline,
        sample_clinical_df,
        sample_proteomics_df,
        sample_rnaseq_df,
        sample_msi_labels,
        sample_gender_labels,
        sample_mismatch_labels,
    ):
        """All 4 stages should appear in results."""
        results = pipeline.run(
            clinical_df=sample_clinical_df,
            proteomics_df=sample_proteomics_df,
            rnaseq_df=sample_rnaseq_df,
            msi_labels=sample_msi_labels,
            gender_labels=sample_gender_labels,
            mismatch_labels=sample_mismatch_labels,
        )
        assert len(results["stages"]) == 4

    def test_handles_missing_data(
        self,
        pipeline,
        sample_clinical_df,
        sample_proteomics_df,
        sample_rnaseq_df,
        sample_msi_labels,
        sample_gender_labels,
        sample_mismatch_labels,
    ):
        """Pipeline should handle input with NaN gracefully."""
        # Add extra NaN
        pro = sample_proteomics_df.copy()
        pro.iloc[:5, :3] = np.nan

        results = pipeline.run(
            clinical_df=sample_clinical_df,
            proteomics_df=pro,
            rnaseq_df=sample_rnaseq_df,
            msi_labels=sample_msi_labels,
            gender_labels=sample_gender_labels,
            mismatch_labels=sample_mismatch_labels,
        )
        assert results["stages"]["impute"]["imputed_proteomics"].isna().sum().sum() == 0

    def test_deterministic_with_seed(
        self,
        sample_clinical_df,
        sample_proteomics_df,
        sample_rnaseq_df,
        sample_msi_labels,
        sample_gender_labels,
        sample_mismatch_labels,
    ):
        """Same seed should produce same results."""
        config = {"random_state": 42, "n_iterations": 5}

        p1 = COSMOInspiredPipeline(config=config)
        r1 = p1.run(
            clinical_df=sample_clinical_df,
            proteomics_df=sample_proteomics_df.copy(),
            rnaseq_df=sample_rnaseq_df.copy(),
            msi_labels=sample_msi_labels.copy(),
            gender_labels=sample_gender_labels.copy(),
            mismatch_labels=sample_mismatch_labels.copy(),
        )

        p2 = COSMOInspiredPipeline(config=config)
        r2 = p2.run(
            clinical_df=sample_clinical_df,
            proteomics_df=sample_proteomics_df.copy(),
            rnaseq_df=sample_rnaseq_df.copy(),
            msi_labels=sample_msi_labels.copy(),
            gender_labels=sample_gender_labels.copy(),
            mismatch_labels=sample_mismatch_labels.copy(),
        )

        # Imputed matrices should be identical
        pd.testing.assert_frame_equal(
            r1["stages"]["impute"]["imputed_proteomics"],
            r2["stages"]["impute"]["imputed_proteomics"],
        )
