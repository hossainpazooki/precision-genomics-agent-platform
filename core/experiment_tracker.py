"""Vertex AI Experiments wrapper for tracking ML experiment runs."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ExperimentTracker:
    """Tracks experiment runs in Vertex AI Experiments.

    Falls back to no-op logging when GCP is not configured.
    """

    def __init__(
        self,
        project: str | None = None,
        location: str = "us-central1",
        experiment_name: str | None = None,
    ) -> None:
        self.enabled = bool(project and experiment_name)
        self.project = project
        self.location = location
        self.experiment_name = experiment_name
        self._initialized = False

    def _ensure_init(self) -> None:
        if self._initialized or not self.enabled:
            return
        try:
            from google.cloud import aiplatform

            aiplatform.init(
                project=self.project,
                location=self.location,
                experiment=self.experiment_name,
            )
            self._initialized = True
        except Exception:
            logger.warning("Failed to initialize Vertex AI Experiments; falling back to no-op")
            self.enabled = False

    def start_run(self, run_name: str) -> None:
        """Start a new experiment run."""
        self._ensure_init()
        if not self.enabled:
            logger.info("[local] Experiment run: %s", run_name)
            return
        from google.cloud import aiplatform

        aiplatform.start_run(run_name)
        logger.info("Started Vertex AI experiment run: %s", run_name)

    def log_metrics(self, metrics: dict[str, float]) -> None:
        """Log scalar metrics to the current run."""
        self._ensure_init()
        if not self.enabled:
            logger.info("[local] Metrics: %s", metrics)
            return
        from google.cloud import aiplatform

        aiplatform.log_metrics(metrics)

    def log_params(self, params: dict[str, Any]) -> None:
        """Log parameters to the current run."""
        self._ensure_init()
        if not self.enabled:
            logger.info("[local] Params: %s", params)
            return
        from google.cloud import aiplatform

        aiplatform.log_params({k: str(v) for k, v in params.items()})

    def log_eval_result(self, eval_result: Any) -> None:
        """Log an EvalResult as Vertex AI metrics."""
        metrics = {
            f"eval_{eval_result.name}_score": eval_result.score,
            f"eval_{eval_result.name}_threshold": eval_result.threshold,
            f"eval_{eval_result.name}_passed": float(eval_result.passed),
        }
        self.log_metrics(metrics)

    def log_classification_metrics(self, metrics: dict[str, float]) -> None:
        """Log classification metrics (F1, precision, recall, AUC)."""
        prefixed = {f"clf_{k}": v for k, v in metrics.items()}
        self.log_metrics(prefixed)

    def end_run(self) -> None:
        """End the current experiment run."""
        if not self.enabled:
            return
        from google.cloud import aiplatform

        aiplatform.end_run()
