"""Ensemble mismatch classifier combining multiple ML strategies.

Trains KNN, LASSO, NSC-proxy, and Random Forest classifiers with both
separate (gender/MSI independently) and joint strategies, then stacks
predictions with a logistic regression meta-learner.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
    from sklearn.metrics import (
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.preprocessing import LabelEncoder, StandardScaler
except ImportError:
    KNeighborsClassifier = None  # type: ignore[assignment,misc]
    LogisticRegression = None  # type: ignore[assignment,misc]
    LogisticRegressionCV = None  # type: ignore[assignment,misc]
    RandomForestClassifier = None  # type: ignore[assignment,misc]
    StratifiedKFold = None  # type: ignore[assignment,misc]
    cross_val_predict = None  # type: ignore[assignment,misc]
    LabelEncoder = None  # type: ignore[assignment,misc]
    StandardScaler = None  # type: ignore[assignment,misc]
    f1_score = None  # type: ignore[assignment,misc]


class EnsembleMismatchClassifier:
    """Ensemble classifier for sample mismatch detection."""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.classifiers_: dict = {}
        self.meta_learner_ = None
        self.scaler_ = None
        self.is_fitted_ = False

    def label_weighted_knn(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        k: int = 5,
    ) -> np.ndarray:
        """Custom k-NN with inverse label-frequency weighting.

        Finds k nearest neighbours, then weights each neighbour's vote by
        1 / class_frequency to counteract class imbalance.
        """
        if KNeighborsClassifier is None:
            raise ImportError("scikit-learn is required")

        actual_k = min(k, len(X_train))
        knn = KNeighborsClassifier(n_neighbors=actual_k, algorithm="auto")
        knn.fit(X_train, y_train)

        # Class frequencies
        classes, counts = np.unique(y_train, return_counts=True)
        freq = dict(zip(classes, counts / len(y_train), strict=False))

        # Get neighbour indices
        neigh_indices = knn.kneighbors(X_test, return_distance=False)

        predictions = np.zeros(len(X_test), dtype=y_train.dtype)
        for i, indices in enumerate(neigh_indices):
            neighbour_labels = y_train[indices]
            # Weighted voting: weight = 1 / frequency
            class_scores: dict = {}
            for label in neighbour_labels:
                weight = 1.0 / max(freq.get(label, 1.0), 1e-10)
                class_scores[label] = class_scores.get(label, 0.0) + weight
            predictions[i] = max(class_scores, key=class_scores.get)

        return predictions

    def _make_base_classifiers(self, multiclass: bool = False) -> dict:
        """Build the 4 base classifier types.

        Parameters
        ----------
        multiclass : bool
            If True, use solvers that support >2 classes (e.g. saga instead of
            liblinear for L1 logistic regression).
        """
        if multiclass:
            lasso = LogisticRegressionCV(
                penalty="l1",
                solver="saga",
                cv=2,
                random_state=self.random_state,
                max_iter=5000,
            )
        else:
            lasso = LogisticRegressionCV(
                penalty="l1",
                solver="liblinear",
                cv=2,
                random_state=self.random_state,
                max_iter=5000,
            )

        return {
            "knn": KNeighborsClassifier(
                n_neighbors=min(5, 3),
                algorithm="auto",
            ),
            "lasso": lasso,
            "nsc_proxy": LogisticRegression(
                penalty="l2",
                solver="lbfgs",
                random_state=self.random_state,
                max_iter=5000,
            ),
            "rf": RandomForestClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=self.random_state,
            ),
        }

    def fit(
        self,
        X: np.ndarray | pd.DataFrame,
        y_gender: np.ndarray | pd.Series,
        y_msi: np.ndarray | pd.Series,
        mismatch_labels: np.ndarray | pd.Series,
    ) -> EnsembleMismatchClassifier:
        """Train base classifiers and meta-learner.

        Trains 4 classifiers x 2 strategies (separate gender+MSI, joint) = 8 models.
        Then trains a logistic regression meta-learner on stacked predictions
        via nested 5-fold cross-validation.
        """
        if LogisticRegression is None:
            raise ImportError("scikit-learn is required")

        X_arr = np.asarray(X) if isinstance(X, pd.DataFrame) else X
        y_gender_arr = np.asarray(y_gender).ravel()
        y_msi_arr = np.asarray(y_msi).ravel()
        mismatch_arr = np.asarray(mismatch_labels).ravel().astype(int)

        # Handle NaN
        if np.any(np.isnan(X_arr)):
            X_arr = np.nan_to_num(X_arr, nan=0.0)

        self.scaler_ = StandardScaler()
        X_scaled = self.scaler_.fit_transform(X_arr)

        # Joint label: combine gender + MSI into 4-class target
        y_joint = y_gender_arr * 10 + y_msi_arr

        # Train base classifiers for each strategy
        base_classifiers = self._make_base_classifiers(multiclass=False)
        joint_classifiers = self._make_base_classifiers(multiclass=True)

        for clf_name, clf_template in base_classifiers.items():
            # Separate strategy: gender
            key_gender = f"{clf_name}_separate_gender"
            clf_g = _clone_estimator(clf_template)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                clf_g.fit(X_scaled, y_gender_arr)
            self.classifiers_[key_gender] = clf_g

            # Separate strategy: MSI
            key_msi = f"{clf_name}_separate_msi"
            clf_m = _clone_estimator(clf_template)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                clf_m.fit(X_scaled, y_msi_arr)
            self.classifiers_[key_msi] = clf_m

            # Joint strategy: 4-class (gender * 10 + MSI)
            key_joint = f"{clf_name}_joint"
            clf_j = _clone_estimator(joint_classifiers[clf_name])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                clf_j.fit(X_scaled, y_joint)
            self.classifiers_[key_joint] = clf_j

        # Meta-learner: stacked predictions -> mismatch label
        n_folds = min(5, min(np.bincount(mismatch_arr)))
        n_folds = max(2, n_folds)

        meta_features = self._generate_meta_features(X_scaled, y_gender_arr, y_msi_arr, n_folds)

        self.meta_learner_ = LogisticRegression(random_state=self.random_state, max_iter=5000)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.meta_learner_.fit(meta_features, mismatch_arr)

        self.is_fitted_ = True
        return self

    def _generate_meta_features(
        self,
        X_scaled: np.ndarray,
        y_gender: np.ndarray,
        y_msi: np.ndarray,
        n_folds: int,
    ) -> np.ndarray:
        """Generate stacked predictions for meta-learner training."""
        meta_cols = []

        y_joint = y_gender * 10 + y_msi
        base_classifiers = self._make_base_classifiers(multiclass=False)
        joint_classifiers = self._make_base_classifiers(multiclass=True)

        for clf_name, clf_template in base_classifiers.items():
            for target_name, y_target in [("gender", y_gender), ("msi", y_msi), ("joint", y_joint)]:
                template = joint_classifiers[clf_name] if target_name == "joint" else clf_template
                clf = _clone_estimator(template)
                cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=self.random_state)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    try:
                        preds = cross_val_predict(clf, X_scaled, y_target, cv=cv)
                    except Exception:
                        preds = np.zeros(len(y_target))
                meta_cols.append(preds)

        return np.column_stack(meta_cols)

    def predict_ensemble(self, X: np.ndarray | pd.DataFrame) -> dict:
        """Generate ensemble predictions with per-classifier breakdown.

        Returns
        -------
        dict
            ensemble_predictions, per_classifier_predictions,
            confidence_scores, strategy_comparison.
        """
        if not self.is_fitted_:
            raise RuntimeError("Classifier not fitted. Call fit() first.")

        X_arr = np.asarray(X) if isinstance(X, pd.DataFrame) else X
        if np.any(np.isnan(X_arr)):
            X_arr = np.nan_to_num(X_arr, nan=0.0)

        X_scaled = self.scaler_.transform(X_arr)

        per_classifier = {}
        meta_cols = []

        for key, clf in self.classifiers_.items():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                preds = clf.predict(X_scaled)
            per_classifier[key] = preds.tolist()
            meta_cols.append(preds)

        meta_features = np.column_stack(meta_cols)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ensemble_preds = self.meta_learner_.predict(meta_features)
            try:
                confidence = self.meta_learner_.predict_proba(meta_features)[:, 1]
            except Exception:
                confidence = np.zeros(len(ensemble_preds))

        # Strategy comparison
        separate_votes = []
        joint_votes = []
        for key, preds in per_classifier.items():
            if "separate" in key:
                separate_votes.append(np.array(preds))
            elif "joint" in key:
                joint_votes.append(np.array(preds))

        strategy_comparison = {
            "separate_agreement": _vote_agreement(separate_votes) if separate_votes else 0.0,
            "joint_agreement": _vote_agreement(joint_votes) if joint_votes else 0.0,
        }

        return {
            "ensemble_predictions": ensemble_preds.tolist(),
            "per_classifier_predictions": per_classifier,
            "confidence_scores": confidence.tolist(),
            "strategy_comparison": strategy_comparison,
        }

    def evaluate(
        self,
        X_test: np.ndarray | pd.DataFrame,
        y_test: np.ndarray | pd.Series,
    ) -> dict:
        """Evaluate ensemble on test data.

        Returns
        -------
        dict
            f1, precision, recall, confusion_matrix, roc_auc.
        """
        if not self.is_fitted_:
            raise RuntimeError("Classifier not fitted. Call fit() first.")

        result = self.predict_ensemble(X_test)
        preds = np.array(result["ensemble_predictions"])
        y_true = np.asarray(y_test).ravel().astype(int)

        metrics: dict = {
            "f1": float(f1_score(y_true, preds, average="weighted", zero_division=0)),
            "precision": float(precision_score(y_true, preds, average="weighted", zero_division=0)),
            "recall": float(recall_score(y_true, preds, average="weighted", zero_division=0)),
            "confusion_matrix": confusion_matrix(y_true, preds).tolist(),
        }

        try:
            confidence = np.array(result["confidence_scores"])
            metrics["roc_auc"] = float(roc_auc_score(y_true, confidence))
        except Exception:
            metrics["roc_auc"] = None

        return metrics


def _clone_estimator(estimator):
    """Clone a scikit-learn estimator."""
    try:
        from sklearn.base import clone

        return clone(estimator)
    except Exception:
        return estimator


def _vote_agreement(vote_arrays: list[np.ndarray]) -> float:
    """Fraction of samples where all voters agree."""
    if not vote_arrays or len(vote_arrays[0]) == 0:
        return 0.0
    stacked = np.column_stack(vote_arrays)
    agree = np.all(stacked == stacked[:, :1], axis=1)
    return float(np.mean(agree))


def get_classifier(random_state: int = 42, prefer_gpu: bool = False):
    """Factory: returns GPU classifier if available and preferred, else CPU."""
    if prefer_gpu:
        try:
            from core.gpu_classifier import GPUEnsembleMismatchClassifier

            return GPUEnsembleMismatchClassifier(random_state=random_state)
        except ImportError:
            pass
    return EnsembleMismatchClassifier(random_state=random_state)
