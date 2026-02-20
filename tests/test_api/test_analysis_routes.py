"""Tests for analysis API routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestAnalyzeEndpoints:
    def test_analyze_biomarkers_returns_workflow_id(self, client):
        """POST /analyze/biomarkers should return a workflow_id."""
        with patch(
            "api.routes.analysis._get_temporal_client", new_callable=AsyncMock, return_value=None
        ):
            response = client.post("/analyze/biomarkers", json={})
            assert response.status_code == 200
            data = response.json()
            assert "workflow_id" in data
            assert data["workflow_id"].startswith("biomarker-")
            assert data["status"] == "pending"

    def test_analyze_biomarkers_with_params(self, client):
        """POST /analyze/biomarkers with custom params."""
        with patch(
            "api.routes.analysis._get_temporal_client", new_callable=AsyncMock, return_value=None
        ):
            response = client.post(
                "/analyze/biomarkers",
                json={"dataset": "test", "target": "gender", "modalities": ["proteomics"]},
            )
            assert response.status_code == 200
            data = response.json()
            assert "workflow_id" in data

    def test_analyze_sample_qc_returns_workflow_id(self, client):
        """POST /analyze/sample-qc should return a workflow_id."""
        with patch(
            "api.routes.analysis._get_temporal_client", new_callable=AsyncMock, return_value=None
        ):
            response = client.post("/analyze/sample-qc", json={})
            assert response.status_code == 200
            data = response.json()
            assert "workflow_id" in data
            assert data["workflow_id"].startswith("qc-")

    def test_analyze_sample_qc_with_params(self, client):
        """POST /analyze/sample-qc with custom params."""
        with patch(
            "api.routes.analysis._get_temporal_client", new_callable=AsyncMock, return_value=None
        ):
            response = client.post(
                "/analyze/sample-qc",
                json={"dataset": "test"},
            )
            assert response.status_code == 200

    def test_get_status_not_found(self, client):
        """GET /analyze/{id}/status should 404 for unknown workflow."""
        with patch(
            "api.routes.analysis._get_temporal_client", new_callable=AsyncMock, return_value=None
        ):
            response = client.get("/analyze/nonexistent-123/status")
            assert response.status_code == 404

    def test_get_status_for_registered_workflow(self, client):
        """GET /analyze/{id}/status should work for locally registered workflow."""
        with patch(
            "api.routes.analysis._get_temporal_client", new_callable=AsyncMock, return_value=None
        ):
            # First create a workflow
            resp = client.post("/analyze/biomarkers", json={})
            wf_id = resp.json()["workflow_id"]

            # Then check its status
            status_resp = client.get(f"/analyze/{wf_id}/status")
            assert status_resp.status_code == 200
            assert status_resp.json()["workflow_id"] == wf_id

    def test_get_report_not_found(self, client):
        """GET /analyze/{id}/report should 404 for unknown workflow."""
        with patch(
            "api.routes.analysis._get_temporal_client", new_callable=AsyncMock, return_value=None
        ):
            response = client.get("/analyze/nonexistent-123/report")
            assert response.status_code == 404

    def test_get_report_not_completed(self, client):
        """GET /analyze/{id}/report should 409 for non-completed workflow."""
        with patch(
            "api.routes.analysis._get_temporal_client", new_callable=AsyncMock, return_value=None
        ):
            resp = client.post("/analyze/biomarkers", json={})
            wf_id = resp.json()["workflow_id"]

            report_resp = client.get(f"/analyze/{wf_id}/report")
            assert report_resp.status_code == 409

    def test_multiple_workflows_tracked(self, client):
        """Multiple workflows should each be tracked independently."""
        with patch(
            "api.routes.analysis._get_temporal_client", new_callable=AsyncMock, return_value=None
        ):
            resp1 = client.post("/analyze/biomarkers", json={})
            resp2 = client.post("/analyze/sample-qc", json={})

            wf1 = resp1.json()["workflow_id"]
            wf2 = resp2.json()["workflow_id"]
            assert wf1 != wf2

            s1 = client.get(f"/analyze/{wf1}/status")
            s2 = client.get(f"/analyze/{wf2}/status")
            assert s1.status_code == 200
            assert s2.status_code == 200

    def test_biomarkers_default_params_accepted(self, client):
        """Empty body should be accepted with default params."""
        with patch(
            "api.routes.analysis._get_temporal_client", new_callable=AsyncMock, return_value=None
        ):
            response = client.post("/analyze/biomarkers", json={})
            assert response.status_code == 200
