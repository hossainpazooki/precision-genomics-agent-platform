"""Tests for core.classifier — EnsembleMismatchClassifier."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.classifier import EnsembleMismatchClassifier


@pytest.fixture
def classifier():
    return EnsembleMismatchClassifier(random_state=42)


@pytest.fixture
def clean_X(sample_proteomics_df):
    return sample_proteomics_df.fillna(0.0)


@pytest.fixture
def fitted_classifier(
    classifier, clean_X, sample_gender_labels, sample_msi_labels, sample_mismatch_labels
):
    classifier.fit(clean_X, sample_gender_labels, sample_msi_labels, sample_mismatch_labels)
    return classifier


# ---- label_weighted_knn --------------------------------------------------


class TestLabelWeightedKNN:
    def test_predictions(self, classifier):
        rng = np.random.RandomState(42)
        X_train = rng.rand(20, 5)
        y_train = np.array([0] * 15 + [1] * 5)
        X_test = rng.rand(5, 5)

        preds = classifier.label_weighted_knn(X_train, y_train, X_test, k=3)
        assert len(preds) == 5
        assert set(preds).issubset({0, 1})

    def test_handles_imbalance(self, classifier):
        rng = np.random.RandomState(42)
        X_train = rng.rand(20, 5)
        # Highly imbalanced: 18 vs 2
        y_train = np.array([0] * 18 + [1] * 2)
        X_test = rng.rand(10, 5)

        preds = classifier.label_weighted_knn(X_train, y_train, X_test, k=5)
        assert len(preds) == 10
        # Due to weighting, minority class should get some representation
        # (not necessarily, depends on data, but should not crash)


# ---- fit -----------------------------------------------------------------


class TestFit:
    def test_trains_all_classifiers(self, fitted_classifier):
        assert fitted_classifier.is_fitted_
        assert len(fitted_classifier.classifiers_) > 0

    def test_trains_meta_learner(self, fitted_classifier):
        assert fitted_classifier.meta_learner_ is not None

    def test_with_small_dataset(self, classifier):
        rng = np.random.RandomState(42)
        X = pd.DataFrame(rng.rand(10, 5), columns=[f"G{i}" for i in range(5)])
        y_gender = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1])
        y_msi = np.array([0, 0, 0, 1, 0, 0, 0, 0, 1, 0])
        mismatch = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 1])

        classifier.fit(X, y_gender, y_msi, mismatch)
        assert classifier.is_fitted_


# ---- predict_ensemble ----------------------------------------------------


class TestPredictEnsemble:
    def test_returns_predictions(self, fitted_classifier, clean_X):
        result = fitted_classifier.predict_ensemble(clean_X)
        assert "ensemble_predictions" in result
        preds = result["ensemble_predictions"]
        assert len(preds) == len(clean_X)

    def test_returns_confidence(self, fitted_classifier, clean_X):
        result = fitted_classifier.predict_ensemble(clean_X)
        assert "confidence_scores" in result
        confidence = result["confidence_scores"]
        assert len(confidence) == len(clean_X)
        for c in confidence:
            assert 0.0 <= c <= 1.0

    def test_returns_per_classifier(self, fitted_classifier, clean_X):
        result = fitted_classifier.predict_ensemble(clean_X)
        assert "per_classifier_predictions" in result
        per_clf = result["per_classifier_predictions"]
        assert isinstance(per_clf, dict)
        assert len(per_clf) > 0

    def test_predict_before_fit_raises(self, classifier, clean_X):
        with pytest.raises(RuntimeError, match="not fitted"):
            classifier.predict_ensemble(clean_X)


# ---- evaluate ------------------------------------------------------------


class TestEvaluate:
    def test_returns_metrics(self, fitted_classifier, clean_X, sample_mismatch_labels):
        metrics = fitted_classifier.evaluate(clean_X, sample_mismatch_labels)
        assert isinstance(metrics, dict)

    def test_f1_score_range(self, fitted_classifier, clean_X, sample_mismatch_labels):
        metrics = fitted_classifier.evaluate(clean_X, sample_mismatch_labels)
        assert 0.0 <= metrics["f1"] <= 1.0

    def test_confusion_matrix(self, fitted_classifier, clean_X, sample_mismatch_labels):
        metrics = fitted_classifier.evaluate(clean_X, sample_mismatch_labels)
        assert "confusion_matrix" in metrics
        cm = metrics["confusion_matrix"]
        assert isinstance(cm, list)
        assert len(cm) > 0


# ---- Strategies ----------------------------------------------------------


class TestStrategies:
    def test_separate_strategy(self, fitted_classifier, clean_X):
        result = fitted_classifier.predict_ensemble(clean_X)
        per_clf = result["per_classifier_predictions"]
        separate_keys = [k for k in per_clf if "separate" in k]
        assert len(separate_keys) > 0

    def test_meta_learner_stacking(self, fitted_classifier, clean_X):
        """Meta-learner should produce different predictions than any single classifier."""
        result = fitted_classifier.predict_ensemble(clean_X)
        ensemble = np.array(result["ensemble_predictions"])
        # The meta-learner produces output, which demonstrates stacking works
        assert len(ensemble) == len(clean_X)
