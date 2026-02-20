"""Multi-strategy feature selection for biomarker discovery.

Implements ANOVA, LASSO, Nearest Shrunken Centroids (PAM), and Random Forest
feature selection methods with ensemble integration.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import pandas as pd

try:
    from scipy.stats import f_oneway
except ImportError:
    f_oneway = None  # type: ignore[assignment]

try:
    from statsmodels.stats.multitest import multipletests
except ImportError:
    multipletests = None  # type: ignore[assignment]

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegressionCV
    from sklearn.model_selection import GridSearchCV, StratifiedKFold
    from sklearn.preprocessing import LabelEncoder, StandardScaler
except ImportError:
    LogisticRegressionCV = None  # type: ignore[assignment,misc]
    RandomForestClassifier = None  # type: ignore[assignment,misc]
    GridSearchCV = None  # type: ignore[assignment,misc]
    StratifiedKFold = None  # type: ignore[assignment,misc]
    LabelEncoder = None  # type: ignore[assignment,misc]
    StandardScaler = None  # type: ignore[assignment,misc]


@dataclass
class SelectedFeature:
    """A single feature selected by a method."""

    name: str
    score: float
    method: str
    p_value: float | None = None
    rank: int = 0


@dataclass
class FeaturePanel:
    """A panel of selected features for a target/modality combination."""

    target: str
    modality: str
    features: list[SelectedFeature] = field(default_factory=list)
    method_agreement: dict[str, list[str]] = field(default_factory=dict)


class MultiStrategySelector:
    """Run multiple feature selection methods and combine results."""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state

    def _prepare_data(
        self, X: pd.DataFrame, y: pd.Series
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """Fill NaN and encode labels."""
        X_clean = X.fillna(0.0).values
        gene_names = list(X.columns)

        if y.dtype == object or isinstance(y.iloc[0], str):
            le = LabelEncoder()
            y_enc = le.fit_transform(y)
        else:
            y_enc = y.values.astype(int)

        return X_clean, y_enc, gene_names

    # ------------------------------------------------------------------
    # ANOVA
    # ------------------------------------------------------------------

    def anova_selection(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        correction: str = "bonferroni",
    ) -> list[SelectedFeature]:
        """Per-gene one-way ANOVA with multiple-testing correction."""
        if f_oneway is None:
            raise ImportError("scipy is required for ANOVA selection")
        if multipletests is None:
            raise ImportError("statsmodels is required for ANOVA correction")

        X_clean, y_enc, gene_names = self._prepare_data(X, y)
        classes = np.unique(y_enc)

        f_stats = []
        p_values = []

        for j in range(X_clean.shape[1]):
            groups = [X_clean[y_enc == c, j] for c in classes]
            # Skip if any group has zero variance
            if any(len(g) < 2 for g in groups):
                f_stats.append(0.0)
                p_values.append(1.0)
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                f_stat, p_val = f_oneway(*groups)
            f_stats.append(float(f_stat) if np.isfinite(f_stat) else 0.0)
            p_values.append(float(p_val) if np.isfinite(p_val) else 1.0)

        # Multiple testing correction
        reject, corrected_p, _, _ = multipletests(p_values, method=correction)

        results: list[SelectedFeature] = []
        for j in range(len(gene_names)):
            if reject[j]:
                results.append(
                    SelectedFeature(
                        name=gene_names[j],
                        score=f_stats[j],
                        method="anova",
                        p_value=corrected_p[j],
                    )
                )

        # Sort by score descending and assign ranks
        results.sort(key=lambda f: f.score, reverse=True)
        for rank, feat in enumerate(results, 1):
            feat.rank = rank

        return results

    # ------------------------------------------------------------------
    # LASSO (L1 Logistic Regression)
    # ------------------------------------------------------------------

    def lasso_selection(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv_folds: int = 10,
    ) -> list[SelectedFeature]:
        """L1-penalized logistic regression; non-zero coefficients = selected."""
        if LogisticRegressionCV is None:
            raise ImportError("scikit-learn is required for LASSO selection")

        X_clean, y_enc, gene_names = self._prepare_data(X, y)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_clean)

        len(np.unique(y_enc))
        n_folds = min(cv_folds, min(np.bincount(y_enc)))
        n_folds = max(2, n_folds)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = LogisticRegressionCV(
                penalty="l1",
                solver="liblinear",
                cv=n_folds,
                random_state=self.random_state,
                max_iter=5000,
            )
            model.fit(X_scaled, y_enc)

        # Extract coefficients
        if len(model.coef_.shape) == 2 and model.coef_.shape[0] > 1:
            importance = np.max(np.abs(model.coef_), axis=0)
        else:
            importance = np.abs(model.coef_).ravel()

        results: list[SelectedFeature] = []
        for j in range(len(gene_names)):
            if importance[j] > 1e-10:
                results.append(
                    SelectedFeature(
                        name=gene_names[j],
                        score=float(importance[j]),
                        method="lasso",
                    )
                )

        results.sort(key=lambda f: f.score, reverse=True)
        for rank, feat in enumerate(results, 1):
            feat.rank = rank

        return results

    # ------------------------------------------------------------------
    # Nearest Shrunken Centroids (Tibshirani PAM)
    # ------------------------------------------------------------------

    def nsc_selection(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv_folds: int = 10,
    ) -> list[SelectedFeature]:
        """Nearest Shrunken Centroids (PAM algorithm) feature selection.

        Custom implementation:
        1. Compute class centroids and overall centroid.
        2. For each threshold delta, shrink class centroids via soft-thresholding.
        3. Classify by nearest shrunken centroid.
        4. Cross-validate delta to minimise classification error.
        5. Genes with zero shrunken difference at optimal delta are eliminated.
        """
        X_clean, y_enc, gene_names = self._prepare_data(X, y)
        classes = np.unique(y_enc)
        n_samples, n_genes = X_clean.shape

        # Overall centroid
        overall_centroid = X_clean.mean(axis=0)

        # Per-class centroids and counts
        class_centroids = {}
        class_counts = {}
        for c in classes:
            mask = y_enc == c
            class_centroids[c] = X_clean[mask].mean(axis=0)
            class_counts[c] = int(mask.sum())

        # Pooled within-class standard deviation
        pooled_var = np.zeros(n_genes)
        for c in classes:
            mask = y_enc == c
            if mask.sum() > 1:
                pooled_var += ((X_clean[mask] - class_centroids[c]) ** 2).sum(axis=0)
        pooled_std = np.sqrt(pooled_var / max(n_samples - len(classes), 1))
        # Avoid division by zero
        pooled_std[pooled_std < 1e-10] = 1e-10

        # Compute raw d_kj = (centroid_k - overall) / (s_j * m_k)
        # where m_k = sqrt(1/n_k + 1/n)
        raw_d = {}
        mk = {}
        for c in classes:
            m = np.sqrt(1.0 / class_counts[c] + 1.0 / n_samples)
            mk[c] = m
            raw_d[c] = (class_centroids[c] - overall_centroid) / (pooled_std * m)

        max_delta = max(np.max(np.abs(d)) for d in raw_d.values())
        if max_delta < 1e-10:
            max_delta = 1.0
        deltas = np.linspace(0, max_delta, 20)

        def _soft_threshold(d: np.ndarray, delta: float) -> np.ndarray:
            return np.sign(d) * np.maximum(np.abs(d) - delta, 0.0)

        def _classify(X_data: np.ndarray, delta: float) -> np.ndarray:
            # Shrunken centroids
            shrunken = {}
            for c in classes:
                d_shrunk = _soft_threshold(raw_d[c], delta)
                shrunken[c] = overall_centroid + pooled_std * mk[c] * d_shrunk

            preds = np.zeros(len(X_data), dtype=int)
            for i in range(len(X_data)):
                best_class = classes[0]
                best_dist = float("inf")
                for c in classes:
                    dist = np.sum((X_data[i] - shrunken[c]) ** 2)
                    if dist < best_dist:
                        best_dist = dist
                        best_class = c
                preds[i] = best_class
            return preds

        # Cross-validate delta
        n_folds = min(cv_folds, min(np.bincount(y_enc)))
        n_folds = max(2, n_folds)

        if StratifiedKFold is not None:
            cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=self.random_state)
            folds = list(cv.split(X_clean, y_enc))
        else:
            # Fallback simple split
            idx = np.arange(n_samples)
            np.random.RandomState(self.random_state).shuffle(idx)
            fold_size = n_samples // n_folds
            folds = []
            for f in range(n_folds):
                test_idx = idx[f * fold_size : (f + 1) * fold_size]
                train_idx = np.setdiff1d(idx, test_idx)
                folds.append((train_idx, test_idx))

        best_delta = 0.0
        best_error = float("inf")

        for delta in deltas:
            errors = []
            for train_idx, test_idx in folds:
                preds = _classify(X_clean[test_idx], delta)
                error = 1.0 - np.mean(preds == y_enc[test_idx])
                errors.append(error)
            mean_error = np.mean(errors)
            if mean_error < best_error:
                best_error = mean_error
                best_delta = delta

        # Select genes: those with non-zero shrunken difference at best_delta
        gene_active = np.zeros(n_genes, dtype=bool)
        gene_scores = np.zeros(n_genes)
        for c in classes:
            d_shrunk = _soft_threshold(raw_d[c], best_delta)
            gene_active |= np.abs(d_shrunk) > 1e-10
            gene_scores += np.abs(d_shrunk)

        results: list[SelectedFeature] = []
        for j in range(n_genes):
            if gene_active[j]:
                results.append(
                    SelectedFeature(
                        name=gene_names[j],
                        score=float(gene_scores[j]),
                        method="nsc",
                    )
                )

        results.sort(key=lambda f: f.score, reverse=True)
        for rank, feat in enumerate(results, 1):
            feat.rank = rank

        return results

    # ------------------------------------------------------------------
    # Random Forest
    # ------------------------------------------------------------------

    def random_forest_selection(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_estimators: int = 500,
        cv_folds: int = 10,
    ) -> list[SelectedFeature]:
        """Random Forest with GridSearchCV; top features by importance."""
        if RandomForestClassifier is None:
            raise ImportError("scikit-learn is required for RF selection")

        X_clean, y_enc, gene_names = self._prepare_data(X, y)

        n_folds = min(cv_folds, min(np.bincount(y_enc)))
        n_folds = max(2, n_folds)

        param_grid = {
            "max_depth": [3, 5, 10],
            "min_samples_leaf": [1, 3],
        }

        base_rf = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=self.random_state,
            n_jobs=-1,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=self.random_state)
            grid = GridSearchCV(
                base_rf,
                param_grid,
                cv=cv,
                scoring="f1_weighted",
                n_jobs=-1,
            )
            grid.fit(X_clean, y_enc)

        best_model = grid.best_estimator_
        importances = best_model.feature_importances_

        # Select features with non-trivial importance
        threshold = 1.0 / len(gene_names) * 0.5  # half of uniform importance
        results: list[SelectedFeature] = []
        for j in range(len(gene_names)):
            if importances[j] > threshold:
                results.append(
                    SelectedFeature(
                        name=gene_names[j],
                        score=float(importances[j]),
                        method="random_forest",
                    )
                )

        results.sort(key=lambda f: f.score, reverse=True)
        for rank, feat in enumerate(results, 1):
            feat.rank = rank

        return results

    # ------------------------------------------------------------------
    # Ensemble integration
    # ------------------------------------------------------------------

    def ensemble_select(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        target: str,
        modality: str,
        strategy: str = "union_weighted",
        n_top: int = 30,
    ) -> FeaturePanel:
        """Run all 4 methods and integrate per strategy.

        Strategies:
        - ``"union_weighted"``: each method votes, weight = 1/rank, sum across
          methods, take top ``n_top``.
        - ``"intersection"``: genes selected by all 4 methods.
        - ``"union"``: genes selected by at least 1 method.
        """
        method_results: dict[str, list[SelectedFeature]] = {}

        for name, method in [
            ("anova", self.anova_selection),
            ("lasso", self.lasso_selection),
            ("nsc", self.nsc_selection),
            ("random_forest", self.random_forest_selection),
        ]:
            try:
                method_results[name] = method(X, y)
            except Exception:
                method_results[name] = []

        # Build method_agreement: gene -> list of methods that selected it
        gene_methods: dict[str, list[str]] = {}
        for method_name, features in method_results.items():
            for feat in features:
                gene_methods.setdefault(feat.name, []).append(method_name)

        if strategy == "intersection":
            # Genes selected by all methods that produced results
            active_methods = [m for m, r in method_results.items() if len(r) > 0]
            if active_methods:
                selected_genes = [
                    g
                    for g, methods in gene_methods.items()
                    if len(methods) >= len(active_methods)
                ]
            else:
                selected_genes = []

        elif strategy == "union":
            selected_genes = list(gene_methods.keys())

        else:  # union_weighted (default)
            gene_weights: dict[str, float] = {}
            for features in method_results.values():
                for feat in features:
                    gene_weights[feat.name] = gene_weights.get(feat.name, 0.0) + (
                        1.0 / max(feat.rank, 1)
                    )

            ranked = sorted(gene_weights.items(), key=lambda x: x[1], reverse=True)
            selected_genes = [g for g, _ in ranked[:n_top]]

        # Build final FeaturePanel
        # Aggregate scores across methods for selected genes
        gene_best_score: dict[str, float] = {}
        gene_best_pvalue: dict[str, float | None] = {}
        for features in method_results.values():
            for feat in features:
                if feat.name in selected_genes:
                    if feat.name not in gene_best_score or feat.score > gene_best_score[feat.name]:
                        gene_best_score[feat.name] = feat.score
                        gene_best_pvalue[feat.name] = feat.p_value

        panel_features: list[SelectedFeature] = []
        for rank, gene in enumerate(selected_genes, 1):
            panel_features.append(
                SelectedFeature(
                    name=gene,
                    score=gene_best_score.get(gene, 0.0),
                    method="ensemble",
                    p_value=gene_best_pvalue.get(gene),
                    rank=rank,
                )
            )

        return FeaturePanel(
            target=target,
            modality=modality,
            features=panel_features,
            method_agreement=gene_methods,
        )
