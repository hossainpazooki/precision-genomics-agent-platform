"""Tests for workflow management API routes."""

from __future__ import annotations

import pytest


class TestRunWorkflow:
    def test_run_biomarker_discovery(self, client):
        response = client.post("/workflows/run?workflow_type=biomarker_discovery")
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data

    def test_run_sample_qc(self, client):
        response = client.post("/workflows/run?workflow_type=sample_qc")
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data

    def test_run_invalid_type(self, client):
        response = client.post("/workflows/run?workflow_type=invalid_type")
        assert response.status_code == 400
        assert "Invalid workflow type" in response.json()["detail"]

    def test_run_with_params(self, client):
        response = client.post(
            "/workflows/run?workflow_type=biomarker_discovery",
            json={"dataset": "test"},
        )
        assert response.status_code == 200


class TestGetWorkflowStatus:
    def test_status_for_known_workflow(self, client):
        post_resp = client.post("/workflows/run?workflow_type=biomarker_discovery")
        wf_id = post_resp.json()["workflow_id"]
        status_resp = client.get(f"/workflows/{wf_id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["workflow_id"] == wf_id

    def test_status_for_unknown_workflow(self, client):
        response = client.get("/workflows/nonexistent-id/status")
        assert response.status_code == 404


class TestCancelWorkflow:
    def test_cancel_known_workflow(self, client):
        post_resp = client.post("/workflows/run?workflow_type=sample_qc")
        wf_id = post_resp.json()["workflow_id"]
        cancel_resp = client.post(f"/workflows/{wf_id}/cancel")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

    def test_cancel_unknown_workflow(self, client):
        response = client.post("/workflows/nonexistent-id/cancel")
        assert response.status_code == 404
