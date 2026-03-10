"""COSMO-inspired 4-stage pipeline orchestrator.

Coordinates the full analysis workflow: imputation, cross-omics matching,
feature selection + classification, and dual validation.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from core.availability import AvailabilityFilter
from core.classifier import EnsembleMismatchClassifier
from core.config import get_settings
from core.cross_omics_matcher import CrossOmicsMatcher
from core.data_loader import OmicsDataLoader
from core.feature_selection import MultiStrategySelector
from core.imputation import OmicsImputer


class COSMOInspiredPipeline:
    """Four-stage pipeline for multi-omics mismatch detection.

    Stage 1 — Impute: Fill missing values (MNAR + MAR).
    Stage 2 — Match: Cross-omics distance matrix + Hungarian matching.
    Stage 3 — Predict: Feature selection + ensemble classification.
    Stage 4 — Correct: Dual validation of mismatches.
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.results_: dict = {}

    def run(
        self,
        dataset: str = "train",
        data_dir: str | None = None,
        clinical_df: pd.DataFrame | None = None,
        proteomics_df: pd.DataFrame | None = None,
        rnaseq_df: pd.DataFrame | None = None,
        msi_labels: pd.Series | None = None,
        gender_labels: pd.Series | None = None,
        mismatch_labels: pd.Series | None = None,
    ) -> dict:
        """Run the complete 4-stage pipeline.

        Data can be provided directly via parameters (for testing) or
        loaded from disk via ``data_dir``.

        Returns
        -------
        dict
            Complete results with per-stage metrics.
        """
        results: dict = {"stages": {}}

        # ---- Load data if not provided ----
        if clinical_df is None:
            loader = OmicsDataLoader(data_dir=data_dir)
            clinical_df = loader.load_clinical(dataset)
            proteomics_df = loader.load_proteomics(dataset)
            rnaseq_df = loader.load_rnaseq(dataset)

        # Build labels from clinical if not provided
        if gender_labels is None and clinical_df is not None and "gender" in clinical_df.columns:
            cdf = clinical_df.set_index("sample_id") if "sample_id" in clinical_df.columns else clinical_df
            gender_labels = pd.Series(
                [1 if g == "Male" else 0 for g in cdf["gender"]],
                index=cdf.index,
                name="gender",
            )

        if msi_labels is None and clinical_df is not None and "MSI_status" in clinical_df.columns:
            cdf = clinical_df.set_index("sample_id") if "sample_id" in clinical_df.columns else clinical_df
            msi_labels = pd.Series(
                [1 if m == "MSI-H" else 0 for m in cdf["MSI_status"]],
                index=cdf.index,
                name="msi",
            )

        if mismatch_labels is None:
            n = len(proteomics_df) if proteomics_df is not None else 0
            idx = proteomics_df.index if proteomics_df is not None else []
            mismatch_labels = pd.Series([0] * n, index=idx, name="is_mislabeled")

        # ---- Stage 1: Impute ----
        stage1 = self._stage_impute(proteomics_df, rnaseq_df, clinical_df)
        results["stages"]["impute"] = stage1

        imputed_prot = stage1["imputed_proteomics"]
        imputed_rna = stage1["imputed_rnaseq"]

        # ---- Stage 2: Match ----
        stage2 = self._stage_match(imputed_prot, imputed_rna)
        results["stages"]["match"] = {k: v for k, v in stage2.items() if k != "distance_matrix"}

        # ---- Stage 3: Predict ----
        stage3 = self._stage_predict(imputed_prot, gender_labels, msi_labels, mismatch_labels)
        results["stages"]["predict"] = stage3

        # ---- Model persistence (optional) ----
        self._persist_model_if_enabled(stage3, results)

        # ---- Stage 4: Correct ----
        classification_flags = stage3.get("flagged_samples", [])
        distance_flags = [m["sample_id"] for m in stage2.get("mismatches", []) if m.get("is_flagged", False)]
        stage4 = self._stage_correct(classification_flags, distance_flags)
        results["stages"]["correct"] = stage4

        self.results_ = results
        return results

    def _stage_impute(
        self,
        proteomics_df: pd.DataFrame | None,
        rnaseq_df: pd.DataFrame | None,
        clinical_df: pd.DataFrame | None,
    ) -> dict:
        """Stage 1: Imputation."""
        imputer = OmicsImputer()
        af = AvailabilityFilter()

        result: dict = {}

        if proteomics_df is not None and clinical_df is not None:
            imputed_prot, prot_stats = imputer.impute(proteomics_df, clinical_df)
            result["imputed_proteomics"] = imputed_prot
            result["proteomics_stats"] = prot_stats

            avail = af.compare_pre_post_imputation(proteomics_df, imputed_prot)
            result["proteomics_availability"] = {
                "before": avail["before_count"],
                "after": avail["after_count"],
                "rescued": len(avail["genes_rescued"]),
            }
        else:
            result["imputed_proteomics"] = proteomics_df

        if rnaseq_df is not None and clinical_df is not None:
            imputed_rna, rna_stats = imputer.impute(rnaseq_df, clinical_df)
            result["imputed_rnaseq"] = imputed_rna
            result["rnaseq_stats"] = rna_stats

            avail = af.compare_pre_post_imputation(rnaseq_df, imputed_rna)
            result["rnaseq_availability"] = {
                "before": avail["before_count"],
                "after": avail["after_count"],
                "rescued": len(avail["genes_rescued"]),
            }
        else:
            result["imputed_rnaseq"] = rnaseq_df

        return result

    def _stage_match(
        self,
        proteomics_df: pd.DataFrame | None,
        rnaseq_df: pd.DataFrame | None,
    ) -> dict:
        """Stage 2: Cross-omics matching."""
        matcher = CrossOmicsMatcher()
        result: dict = {}

        if proteomics_df is None or rnaseq_df is None:
            result["mismatches"] = []
            return result

        shared_genes = sorted(set(proteomics_df.columns) & set(rnaseq_df.columns))
        shared_samples = sorted(set(proteomics_df.index) & set(rnaseq_df.index))

        if not shared_genes or not shared_samples:
            result["mismatches"] = []
            return result

        correlations = matcher.compute_gene_correlations(proteomics_df, rnaseq_df)
        result["gene_correlations_summary"] = {
            "n_genes": len(correlations),
            "mean_r2": float(correlations["r_squared"].mean()) if len(correlations) > 0 else 0.0,
        }

        n_iter = self.config.get("n_iterations", 20)
        sampling_frac = self.config.get("sampling_fraction", 0.8)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dist = matcher.build_distance_matrix(proteomics_df, rnaseq_df, shared_genes)

        result["distance_matrix"] = dist

        mismatches = matcher.identify_mismatches(
            dist,
            shared_samples,
            n_iterations=n_iter,
            sampling_fraction=sampling_frac,
        )
        result["mismatches"] = mismatches
        result["n_flagged"] = sum(1 for m in mismatches if m["is_flagged"])

        return result

    def _stage_predict(
        self,
        expression_df: pd.DataFrame | None,
        gender_labels: pd.Series | None,
        msi_labels: pd.Series | None,
        mismatch_labels: pd.Series | None,
    ) -> dict:
        """Stage 3: Feature selection + classification."""
        result: dict = {}

        if expression_df is None or gender_labels is None or msi_labels is None:
            result["flagged_samples"] = []
            return result

        # Align indices
        common = sorted(set(expression_df.index) & set(gender_labels.index) & set(msi_labels.index))
        if not common:
            result["flagged_samples"] = []
            return result

        X = expression_df.loc[common]
        y_gender = gender_labels.loc[common]
        y_msi = msi_labels.loc[common]
        y_mismatch = (
            mismatch_labels.loc[common] if mismatch_labels is not None else pd.Series([0] * len(common), index=common)
        )

        # Feature selection
        selector = MultiStrategySelector(random_state=self.config.get("random_state", 42))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                panel = selector.ensemble_select(
                    X,
                    y_msi,
                    target="msi",
                    modality="proteomics",
                    n_top=self.config.get("n_top_features", 30),
                )
                result["feature_panel"] = {
                    "n_features": len(panel.features),
                    "top_features": [f.name for f in panel.features[:10]],
                }

                if panel.features:
                    selected_genes = [f.name for f in panel.features if f.name in X.columns]
                    if selected_genes:
                        X = X[selected_genes]
            except Exception as e:
                result["feature_selection_error"] = str(e)

        # Classification
        classifier = EnsembleMismatchClassifier(random_state=self.config.get("random_state", 42))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                classifier.fit(X, y_gender, y_msi, y_mismatch)
                pred_result = classifier.predict_ensemble(X)
                preds = pred_result["ensemble_predictions"]

                flagged = [common[i] for i, p in enumerate(preds) if p == 1]
                result["flagged_samples"] = flagged
                result["_classifier"] = classifier
                result["classification_result"] = {
                    "n_flagged": len(flagged),
                    "confidence_mean": float(np.mean(pred_result["confidence_scores"])),
                }
            except Exception as e:
                result["classification_error"] = str(e)
                result["flagged_samples"] = []

        return result

    def _persist_model_if_enabled(self, stage3: dict, results: dict) -> None:
        """Optionally serialize, upload, and register the trained model."""
        settings = get_settings()
        if not settings.persist_models:
            return

        try:
            from core.model_registry import register_with_vertex, save_to_gcs, serialize_model

            classifier = stage3.get("_classifier")
            if classifier is None:
                return

            metadata = {
                "classification_result": stage3.get("classification_result", {}),
                "feature_panel": stage3.get("feature_panel", {}),
            }
            artifact = serialize_model(classifier, metadata)

            if settings.gcs_model_bucket:
                import uuid

                run_id = str(uuid.uuid4())[:8]
                path = f"models/{run_id}/model.joblib"
                artifact_uri = save_to_gcs(artifact, settings.gcs_model_bucket, path)
                results["model_artifact_uri"] = artifact_uri

                if settings.register_vertex_models:
                    register_with_vertex(
                        artifact_uri=f"gs://{settings.gcs_model_bucket}/models/{run_id}",
                        display_name=f"precision-genomics-{run_id}",
                        labels={"pipeline": "cosmo-inspired"},
                        project=settings.gcp_project_id,
                        location=settings.gcp_region,
                    )
        except Exception:
            import logging

            logging.getLogger(__name__).warning("Model persistence failed", exc_info=True)

    def _stage_correct(
        self,
        classification_flags: list[str],
        distance_flags: list[str],
    ) -> dict:
        """Stage 4: Dual validation."""
        matcher = CrossOmicsMatcher()
        validations = matcher.dual_validate(classification_flags, distance_flags)

        high_confidence = [v for v in validations if v["concordance_level"] == "HIGH"]
        review = [v for v in validations if v["concordance_level"] == "REVIEW"]

        return {
            "validations": validations,
            "n_high_confidence": len(high_confidence),
            "n_review": len(review),
            "high_confidence_samples": [v["sample_id"] for v in high_confidence],
            "review_samples": [v["sample_id"] for v in review],
        }
