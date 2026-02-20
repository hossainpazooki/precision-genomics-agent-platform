"""Tests for biomarker panel API routes."""

from __future__ import annotations

import pytest


class TestListPanels:
    def test_list_returns_panels(self, client):
        response = client.get("/biomarkers/panels")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_panel_has_required_fields(self, client):
        response = client.get("/biomarkers/panels")
        data = response.json()
        for panel in data:
            assert "id" in panel
            assert "target" in panel
            assert "modality" in panel

    def test_panels_include_msi(self, client):
        response = client.get("/biomarkers/panels")
        data = response.json()
        targets = [p["target"] for p in data]
        assert "msi" in targets


class TestGetPanelFeatures:
    def test_get_existing_panel(self, client):
        response = client.get("/biomarkers/1/features")
        assert response.status_code == 200
        data = response.json()
        assert data["panel_id"] == 1
        assert "features" in data
        assert isinstance(data["features"], list)

    def test_get_nonexistent_panel(self, client):
        response = client.get("/biomarkers/999/features")
        assert response.status_code == 404

    def test_panel_features_have_gene_field(self, client):
        response = client.get("/biomarkers/1/features")
        data = response.json()
        for feature in data["features"]:
            assert "gene" in feature
