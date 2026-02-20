"""MCP tool: Run ensemble classification."""

from __future__ import annotations

from core.classifier import EnsembleMismatchClassifier
from mcp_server.schemas.omics import RunClassificationInput, RunClassificationOutput


async def run_tool(
    input_data: RunClassificationInput,
    X_train=None,
    y_gender=None,
    y_msi=None,
    mismatch_labels=None,
    X_test=None,
    y_test=None,
) -> RunClassificationOutput:
    """Run ensemble mismatch classification.

    Delegates to ``core.classifier.EnsembleMismatchClassifier``.

    Parameters
    ----------
    input_data : RunClassificationInput
        Tool input schema.
    X_train, y_gender, y_msi, mismatch_labels :
        Training data for the ensemble classifier.
    X_test, y_test :
        Test data for evaluation.
    """
    clf = EnsembleMismatchClassifier()
    clf.fit(X_train, y_gender, y_msi, mismatch_labels)

    predictions = clf.predict_ensemble(X_train)

    # Evaluate if test data provided
    metrics: dict = {}
    if X_test is not None and y_test is not None:
        metrics = clf.evaluate(X_test, y_test)

    ensemble_f1 = metrics.get("f1", predictions.get("ensemble_f1", 0.0))
    per_clf_f1 = metrics.get("per_classifier_f1", predictions.get("per_classifier_f1", {}))

    # Strategy comparison
    strategy_comparison = predictions.get("strategy_comparison", {
        input_data.phenotype_strategy: ensemble_f1,
    })

    # Feature importances from predictions
    importances = predictions.get("feature_importances", [])

    return RunClassificationOutput(
        ensemble_f1=ensemble_f1,
        per_classifier_f1=per_clf_f1,
        best_strategy=input_data.phenotype_strategy,
        strategy_comparison=strategy_comparison,
        feature_importances=importances,
        comparison_to_baseline={
            "baseline_f1": 0.50,
            "improvement": round(ensemble_f1 - 0.50, 4),
        },
    )
