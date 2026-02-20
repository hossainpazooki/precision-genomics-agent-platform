"""Tests for analysis API routes."""

from __future__ import annotations

import pytest


class TestStartBiomarkerAnalysis:
    def test_start_biomarker_default_params(self, client):
        response = client.post("/analyze/biomarkers", json={})
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert data["workflow_id"].startswith("biomarker-")

    def test_start_biomarker_custom_params(self, client):
        response = client.post("/analyze/biomarkers", json={
            "dataset": "test",
            "target": "gender",
            "modalities": ["proteomics"],
            "n_top_features": 50,
        })
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data

    def test_start_biomarker_returns_status(self, client):
        response = client.post("/analyze/biomarkers", json={})
        data = response.json()
        assert "status" in data


class TestStartSampleQC:
    def test_start_sample_qc_default(self, client):
        response = client.post("/analyze/sample-qc", json={})
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert data["workflow_id"].startswith("sample-qc-")

    def test_start_sample_qc_custom(self, client):
        response = client.post("/analyze/sample-qc", json={
            "dataset": "test",
            "n_iterations": 50,
        })
        assert response.status_code == 200


class TestGetAnalysisStatus:
    def test_status_for_known_workflow(self, client):
        post_resp = client.post("/analyze/biomarkers", json={})
        wf_id = post_resp.json()["workflow_id"]
        status_resp = client.get(f"/analyze/{wf_id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["workflow_id"] == wf_id

    def test_status_for_unknown_workflow(self, client):
        response = client.get("/analyze/nonexistent-id/status")
        assert response.status_code == 404


class TestGetAnalysisReport:
    def test_report_for_pending_workflow(self, client):
        post_resp = client.post("/analyze/biomarkers", json={})
        wf_id = post_resp.json()["workflow_id"]
        report_resp = client.get(f"/analyze/{wf_id}/report")
        assert report_resp.status_code == 200
        data = report_resp.json()
        assert data["workflow_id"] == wf_id

    def test_report_for_unknown_workflow(self, client):
        response = client.get("/analyze/nonexistent-id/report")
        assert response.status_code == 404
