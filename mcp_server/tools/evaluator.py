"""MCP tool: Evaluate trained model on holdout or cross-validation."""

from __future__ import annotations

from mcp_server.schemas.omics import EvaluateModelInput, EvaluateModelOutput


async def run_tool(
    input_data: EvaluateModelInput,
    classifier=None,
    X_test=None,
    y_test=None,
) -> EvaluateModelOutput:
    """Evaluate the ensemble classifier.

    Delegates to ``core.classifier.EnsembleMismatchClassifier.evaluate()``.

    Parameters
    ----------
    input_data : EvaluateModelInput
        Tool input schema.
    classifier : EnsembleMismatchClassifier, optional
        Pre-fitted classifier instance.
    X_test : pd.DataFrame, optional
        Test feature matrix.
    y_test : pd.Series, optional
        Test labels.
    """
    if classifier is None:
        from core.classifier import EnsembleMismatchClassifier

        classifier = EnsembleMismatchClassifier()

    metrics = classifier.evaluate(X_test, y_test)

    f1 = metrics.get("f1", 0.0)
    precision = metrics.get("precision", 0.0)
    recall = metrics.get("recall", 0.0)
    confusion = metrics.get("confusion_matrix", [[0, 0], [0, 0]])
    roc_auc = metrics.get("roc_auc", 0.0)

    baseline_comparison: dict[str, float] = {}
    if input_data.compare_to_baseline:
        baseline_f1 = 0.50
        baseline_comparison = {
            "baseline_f1": baseline_f1,
            "improvement": round(f1 - baseline_f1, 4),
            "relative_gain": round((f1 - baseline_f1) / max(baseline_f1, 1e-6), 4),
        }

    return EvaluateModelOutput(
        f1_score=f1,
        precision=precision,
        recall=recall,
        confusion_matrix=confusion if isinstance(confusion, list) else confusion.tolist(),
        roc_auc=roc_auc,
        baseline_comparison=baseline_comparison,
    )
