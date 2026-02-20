"""Tests for mcp_server.tools.evaluator."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from mcp_server.schemas.omics import EvaluateModelInput, EvaluateModelOutput


@pytest.fixture
def mock_clf():
    """Create a mock EnsembleMismatchClassifier with evaluate method."""
    clf = MagicMock()
    clf.evaluate.return_value = {
        "f1": 0.88,
        "precision": 0.90,
        "recall": 0.86,
        "confusion_matrix": [[15, 2], [1, 2]],
        "roc_auc": 0.91,
    }
    return clf


@pytest.fixture
def sample_test_data():
    rng = np.random.RandomState(42)
    X = pd.DataFrame(rng.rand(20, 10), columns=[f"gene_{i}" for i in range(10)])
    y = pd.Series([0] * 17 + [1] * 3, name="mismatch")
    return X, y


@pytest.mark.asyncio
async def test_evaluate_default(mock_clf, sample_test_data):
    """Test evaluation with default parameters."""
    X, y = sample_test_data
    from mcp_server.tools.evaluator import run_tool

    inp = EvaluateModelInput()
    result = await run_tool(inp, classifier=mock_clf, X_test=X, y_test=y)

    assert isinstance(result, EvaluateModelOutput)
    assert result.f1_score == 0.88


@pytest.mark.asyncio
async def test_evaluate_precision_recall(mock_clf, sample_test_data):
    """Test precision and recall are reported."""
    X, y = sample_test_data
    inp = EvaluateModelInput()
    from mcp_server.tools.evaluator import run_tool

    result = await run_tool(inp, classifier=mock_clf, X_test=X, y_test=y)

    assert result.precision == 0.90
    assert result.recall == 0.86


@pytest.mark.asyncio
async def test_evaluate_confusion_matrix(mock_clf, sample_test_data):
    """Test confusion matrix is returned."""
    X, y = sample_test_data
    inp = EvaluateModelInput()
    from mcp_server.tools.evaluator import run_tool

    result = await run_tool(inp, classifier=mock_clf, X_test=X, y_test=y)

    assert isinstance(result.confusion_matrix, list)
    assert len(result.confusion_matrix) == 2


@pytest.mark.asyncio
async def test_evaluate_roc_auc(mock_clf, sample_test_data):
    """Test ROC-AUC is reported."""
    X, y = sample_test_data
    inp = EvaluateModelInput()
    from mcp_server.tools.evaluator import run_tool

    result = await run_tool(inp, classifier=mock_clf, X_test=X, y_test=y)

    assert result.roc_auc == 0.91


@pytest.mark.asyncio
async def test_evaluate_baseline_comparison(mock_clf, sample_test_data):
    """Test baseline comparison when enabled."""
    X, y = sample_test_data
    inp = EvaluateModelInput(compare_to_baseline=True)
    from mcp_server.tools.evaluator import run_tool

    result = await run_tool(inp, classifier=mock_clf, X_test=X, y_test=y)

    assert "baseline_f1" in result.baseline_comparison
    assert "improvement" in result.baseline_comparison
    assert result.baseline_comparison["improvement"] == pytest.approx(0.38, abs=0.01)


@pytest.mark.asyncio
async def test_evaluate_no_baseline_comparison(mock_clf, sample_test_data):
    """Test that baseline comparison is empty when disabled."""
    X, y = sample_test_data
    inp = EvaluateModelInput(compare_to_baseline=False)
    from mcp_server.tools.evaluator import run_tool

    result = await run_tool(inp, classifier=mock_clf, X_test=X, y_test=y)

    assert result.baseline_comparison == {}
