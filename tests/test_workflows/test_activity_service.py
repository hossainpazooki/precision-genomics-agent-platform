"""Tests for the activity service HTTP endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from workflows.activity_service import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestActivityServiceHealth:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert isinstance(data["activities"], list)
        assert len(data["activities"]) > 0

    def test_registered_activities(self, client):
        response = client.get("/health")
        activities = response.json()["activities"]
        expected = [
            "load_and_validate_data",
            "impute_data",
            "select_features",
            "integrate_and_filter",
            "train_and_evaluate",
            "generate_interpretation",
            "compile_report",
            "cross_validate_flags",
            "quarantine_samples",
        ]
        for name in expected:
            assert name in activities


class TestActivityServiceEndpoints:
    def test_unknown_activity_returns_404(self, client):
        response = client.post("/activities/nonexistent", json={"args": []})
        assert response.status_code == 404

    def test_quarantine_activity(self, client):
        response = client.post(
            "/activities/quarantine_samples",
            json={"args": [["S001", "S002"]]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["result"]["n_quarantined"] == 2

    def test_cross_validate_flags_activity(self, client):
        response = client.post(
            "/activities/cross_validate_flags",
            json={"args": [["S001", "S002"], ["S002", "S003"]]},
        )
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["n_concordant"] == 1
        assert result["total_flagged"] == 3

    def test_integrate_and_filter_activity(self, client):
        panels = [
            {"modality": "proteomics", "features": ["TAP1", "LCP1"]},
            {"modality": "rnaseq", "features": ["LCP1", "IRF1"]},
        ]
        response = client.post(
            "/activities/integrate_and_filter",
            json={"args": [panels]},
        )
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["n_total"] == 3
        assert "TAP1" in result["features"]

    def test_train_and_evaluate_no_features(self, client):
        response = client.post(
            "/activities/train_and_evaluate",
            json={"args": ["test", [], "msi"]},
        )
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["accuracy"] == 0.0

    def test_compare_and_deploy_activity(self, client):
        response = client.post(
            "/activities/compare_and_deploy",
            json={
                "args": [{
                    "baseline_score": 0.80,
                    "optimized_score": 0.90,
                    "module": "biomarker_discovery",
                    "improvement_threshold": 0.05,
                }]
            },
        )
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["deployed"] is True
