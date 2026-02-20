"""Tests for mcp_server.tools.classifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from mcp_server.schemas.omics import RunClassificationInput, RunClassificationOutput


@pytest.fixture
def mock_clf():
    """Create a mock EnsembleMismatchClassifier."""
    clf = MagicMock()
    clf.fit.return_value = None
    clf.predict_ensemble.return_value = {
        "ensemble_f1": 0.92,
        "per_classifier_f1": {"svm": 0.88, "rf": 0.91, "lr": 0.90},
        "strategy_comparison": {"both": 0.92, "gender_only": 0.85},
        "feature_importances": [
            {"gene": "TAP1", "importance": 0.15},
            {"gene": "GBP1", "importance": 0.12},
        ],
    }
    clf.evaluate.return_value = {
        "f1": 0.90,
        "per_classifier_f1": {"svm": 0.87, "rf": 0.89},
    }
    return clf


@pytest.fixture
def sample_data():
    """Create sample training data."""
    rng = np.random.RandomState(42)
    X = pd.DataFrame(rng.rand(20, 10), columns=[f"gene_{i}" for i in range(10)])
    y_gender = pd.Series([1] * 10 + [0] * 10, name="gender")
    y_msi = pd.Series([1] * 3 + [0] * 17, name="msi")
    mismatch = pd.Series([False] * 18 + [True] * 2, name="mismatch")
    return X, y_gender, y_msi, mismatch


@pytest.mark.asyncio
async def test_classification_default(mock_clf, sample_data):
    """Test classification with default parameters."""
    X, y_gender, y_msi, mismatch = sample_data
    with patch("core.classifier.EnsembleMismatchClassifier", return_value=mock_clf):
        from mcp_server.tools.classifier import run_tool

        inp = RunClassificationInput()
        result = await run_tool(inp, X_train=X, y_gender=y_gender, y_msi=y_msi, mismatch_labels=mismatch)

    assert isinstance(result, RunClassificationOutput)
    assert result.ensemble_f1 == 0.92


@pytest.mark.asyncio
async def test_classification_per_classifier_f1(mock_clf, sample_data):
    """Test per-classifier F1 scores are reported."""
    X, y_gender, y_msi, mismatch = sample_data
    with patch("core.classifier.EnsembleMismatchClassifier", return_value=mock_clf):
        from mcp_server.tools.classifier import run_tool

        inp = RunClassificationInput()
        result = await run_tool(inp, X_train=X, y_gender=y_gender, y_msi=y_msi, mismatch_labels=mismatch)

    assert "svm" in result.per_classifier_f1
    assert "rf" in result.per_classifier_f1


@pytest.mark.asyncio
async def test_classification_strategy_comparison(mock_clf, sample_data):
    """Test strategy comparison reporting."""
    X, y_gender, y_msi, mismatch = sample_data
    with patch("core.classifier.EnsembleMismatchClassifier", return_value=mock_clf):
        from mcp_server.tools.classifier import run_tool

        inp = RunClassificationInput()
        result = await run_tool(inp, X_train=X, y_gender=y_gender, y_msi=y_msi, mismatch_labels=mismatch)

    assert isinstance(result.strategy_comparison, dict)


@pytest.mark.asyncio
async def test_classification_feature_importances(mock_clf, sample_data):
    """Test feature importances are returned."""
    X, y_gender, y_msi, mismatch = sample_data
    with patch("core.classifier.EnsembleMismatchClassifier", return_value=mock_clf):
        from mcp_server.tools.classifier import run_tool

        inp = RunClassificationInput()
        result = await run_tool(inp, X_train=X, y_gender=y_gender, y_msi=y_msi, mismatch_labels=mismatch)

    assert len(result.feature_importances) == 2
    assert result.feature_importances[0]["gene"] == "TAP1"


@pytest.mark.asyncio
async def test_classification_baseline_comparison(mock_clf, sample_data):
    """Test baseline comparison is computed."""
    X, y_gender, y_msi, mismatch = sample_data
    with patch("core.classifier.EnsembleMismatchClassifier", return_value=mock_clf):
        from mcp_server.tools.classifier import run_tool

        inp = RunClassificationInput()
        result = await run_tool(inp, X_train=X, y_gender=y_gender, y_msi=y_msi, mismatch_labels=mismatch)

    assert "baseline_f1" in result.comparison_to_baseline
    assert "improvement" in result.comparison_to_baseline


@pytest.mark.asyncio
async def test_classification_fit_called(mock_clf, sample_data):
    """Test that fit is called on the classifier."""
    X, y_gender, y_msi, mismatch = sample_data
    with patch("mcp_server.tools.classifier.EnsembleMismatchClassifier", return_value=mock_clf):
        from mcp_server.tools.classifier import run_tool

        inp = RunClassificationInput()
        await run_tool(inp, X_train=X, y_gender=y_gender, y_msi=y_msi, mismatch_labels=mismatch)

    mock_clf.fit.assert_called_once_with(X, y_gender, y_msi, mismatch)
    mock_clf.predict_ensemble.assert_called_once()
