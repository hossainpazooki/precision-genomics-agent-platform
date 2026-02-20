"""Tests for workflow management API routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestWorkflowEndpoints:
    def test_run_workflow_biomarker_discovery(self, client):
        """POST /workflows/run with biomarker_discovery type."""
        with patch(
            "api.routes.workflows._get_temporal_client",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.post(
                "/workflows/run",
                params={"workflow_type": "biomarker_discovery"},
                json={},
            )
            assert response.status_code == 200
            data = response.json()
            assert "workflow_id" in data
            assert data["workflow_id"].startswith("biomarker_discovery-")

    def test_run_workflow_sample_qc(self, client):
        """POST /workflows/run with sample_qc type."""
        with patch(
            "api.routes.workflows._get_temporal_client",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.post(
                "/workflows/run",
                params={"workflow_type": "sample_qc"},
                json={},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["workflow_id"].startswith("sample_qc-")

    def test_run_workflow_returns_pending_without_temporal(self, client):
        """Without Temporal, workflow should be PENDING."""
        with patch(
            "api.routes.workflows._get_temporal_client",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.post(
                "/workflows/run",
                params={"workflow_type": "biomarker_discovery"},
                json={},
            )
            assert response.json()["status"] == "pending"

    def test_get_workflow_status_not_found(self, client):
        """GET /workflows/{id}/status should 404 without Temporal."""
        with patch(
            "api.routes.workflows._get_temporal_client",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.get("/workflows/nonexistent-123/status")
            assert response.status_code == 404

    def test_cancel_workflow_no_temporal(self, client):
        """POST /workflows/{id}/cancel should 503 without Temporal."""
        with patch(
            "api.routes.workflows._get_temporal_client",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.post("/workflows/nonexistent-123/cancel")
            assert response.status_code == 503

    def test_cancel_workflow_with_temporal(self, client):
        """POST /workflows/{id}/cancel should succeed with Temporal."""
        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle.return_value = mock_handle

        with patch(
            "api.routes.workflows._get_temporal_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            response = client.post("/workflows/wf-001/cancel")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "cancelled"

    def test_get_status_with_temporal(self, client):
        """GET /workflows/{id}/status should return status from Temporal."""
        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        mock_desc = MagicMock()
        mock_desc.status.name = "RUNNING"
        mock_desc.run_id = "run-001"
        mock_desc.workflow_type = "BiomarkerDiscoveryWorkflow"
        mock_desc.start_time = None
        mock_desc.close_time = None
        mock_handle.describe.return_value = mock_desc
        mock_client.get_workflow_handle.return_value = mock_handle

        with patch(
            "api.routes.workflows._get_temporal_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            response = client.get("/workflows/wf-001/status")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"

    def test_run_workflow_with_params(self, client):
        """POST /workflows/run should accept custom params."""
        with patch(
            "api.routes.workflows._get_temporal_client",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.post(
                "/workflows/run",
                params={"workflow_type": "biomarker_discovery"},
                json={"dataset": "test", "target": "gender"},
            )
            assert response.status_code == 200
