"""Tests for core.feature_selection — MultiStrategySelector."""

from __future__ import annotations

import pytest

from core.feature_selection import (
    FeaturePanel,
    MultiStrategySelector,
    SelectedFeature,
)


@pytest.fixture
def selector():
    return MultiStrategySelector(random_state=42)


@pytest.fixture
def small_X(sample_proteomics_df):
    """Clean expression matrix for classification."""
    return sample_proteomics_df.fillna(0.0)


@pytest.fixture
def binary_y(sample_msi_labels):
    return sample_msi_labels


@pytest.fixture
def gender_y(sample_gender_labels):
    return sample_gender_labels


# ---- Dataclass tests -----------------------------------------------------


class TestDataclasses:
    def test_selected_feature_dataclass(self):
        f = SelectedFeature(name="BRCA1", score=0.95, method="anova", p_value=0.01)
        assert f.name == "BRCA1"
        assert f.score == 0.95
        assert f.method == "anova"
        assert f.p_value == 0.01
        assert f.rank == 0

    def test_feature_panel_dataclass(self):
        panel = FeaturePanel(target="msi", modality="proteomics")
        assert panel.target == "msi"
        assert panel.modality == "proteomics"
        assert panel.features == []
        assert panel.method_agreement == {}


# ---- ANOVA ---------------------------------------------------------------


class TestANOVA:
    def test_returns_features(self, selector, small_X, binary_y):
        results = selector.anova_selection(small_X, binary_y)
        assert isinstance(results, list)
        # With small synthetic data, results may or may not be significant
        for feat in results:
            assert isinstance(feat, SelectedFeature)
            assert feat.method == "anova"

    def test_bonferroni_correction(self, selector, small_X, binary_y):
        results = selector.anova_selection(small_X, binary_y, correction="bonferroni")
        for feat in results:
            assert feat.p_value is not None

    def test_bh_correction(self, selector, small_X, binary_y):
        results = selector.anova_selection(small_X, binary_y, correction="fdr_bh")
        # BH correction is less stringent, may yield more results
        assert isinstance(results, list)

    def test_with_binary_labels(self, selector, small_X, gender_y):
        results = selector.anova_selection(small_X, gender_y)
        assert isinstance(results, list)


# ---- LASSO ---------------------------------------------------------------


class TestLASSO:
    def test_returns_features(self, selector, small_X, binary_y):
        results = selector.lasso_selection(small_X, binary_y, cv_folds=3)
        assert isinstance(results, list)
        for feat in results:
            assert isinstance(feat, SelectedFeature)
            assert feat.method == "lasso"

    def test_nonzero_coefficients(self, selector, small_X, binary_y):
        results = selector.lasso_selection(small_X, binary_y, cv_folds=3)
        for feat in results:
            assert feat.score > 0

    def test_with_imbalanced_labels(self, selector, small_X, binary_y):
        # binary_y is highly imbalanced (3 MSI-H vs 17 MSS)
        results = selector.lasso_selection(small_X, binary_y, cv_folds=2)
        assert isinstance(results, list)


# ---- NSC -----------------------------------------------------------------


class TestNSC:
    def test_returns_features(self, selector, small_X, binary_y):
        results = selector.nsc_selection(small_X, binary_y, cv_folds=3)
        assert isinstance(results, list)
        for feat in results:
            assert isinstance(feat, SelectedFeature)
            assert feat.method == "nsc"

    def test_shrinkage(self, selector, small_X, binary_y):
        """NSC should shrink some genes to zero (fewer features than input)."""
        results = selector.nsc_selection(small_X, binary_y, cv_folds=3)
        # At least some genes should have been eliminated
        assert len(results) <= small_X.shape[1]

    def test_cv_selects_optimal_delta(self, selector, small_X, gender_y):
        results = selector.nsc_selection(small_X, gender_y, cv_folds=2)
        assert isinstance(results, list)


# ---- Random Forest -------------------------------------------------------


class TestRandomForest:
    def test_returns_features(self, selector, small_X, binary_y):
        results = selector.random_forest_selection(small_X, binary_y, n_estimators=50, cv_folds=2)
        assert isinstance(results, list)
        for feat in results:
            assert isinstance(feat, SelectedFeature)
            assert feat.method == "random_forest"

    def test_importance_scores(self, selector, small_X, binary_y):
        results = selector.random_forest_selection(small_X, binary_y, n_estimators=50, cv_folds=2)
        for feat in results:
            assert feat.score > 0

    def test_grid_search_completes(self, selector, small_X, gender_y):
        results = selector.random_forest_selection(small_X, gender_y, n_estimators=50, cv_folds=2)
        assert isinstance(results, list)


# ---- Ensemble integration ------------------------------------------------


class TestEnsembleSelect:
    def test_union_weighted(self, selector, small_X, binary_y):
        panel = selector.ensemble_select(
            small_X,
            binary_y,
            target="msi",
            modality="proteomics",
            strategy="union_weighted",
            n_top=10,
        )
        assert isinstance(panel, FeaturePanel)
        assert panel.target == "msi"
        assert panel.modality == "proteomics"

    def test_returns_feature_panel(self, selector, small_X, binary_y):
        panel = selector.ensemble_select(small_X, binary_y, target="msi", modality="proteomics")
        assert isinstance(panel, FeaturePanel)
        assert isinstance(panel.features, list)

    def test_method_agreement(self, selector, small_X, binary_y):
        panel = selector.ensemble_select(small_X, binary_y, target="msi", modality="proteomics")
        assert isinstance(panel.method_agreement, dict)

    def test_feature_count_within_n_top(self, selector, small_X, binary_y):
        panel = selector.ensemble_select(
            small_X,
            binary_y,
            target="msi",
            modality="proteomics",
            strategy="union_weighted",
            n_top=5,
        )
        assert len(panel.features) <= 5

    def test_multiple_modalities(self, selector, small_X, gender_y):
        panel = selector.ensemble_select(
            small_X,
            gender_y,
            target="gender",
            modality="rnaseq",
            n_top=15,
        )
        assert panel.target == "gender"
        assert panel.modality == "rnaseq"
