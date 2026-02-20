"""Tests for biomarker panel API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestBiomarkerEndpoints:
    def test_list_panels_empty(self, client):
        """GET /biomarkers/panels should return empty list when DB unavailable."""
        with patch("api.routes.biomarkers.get_session") as mock_session:
            # Simulate DB unavailable
            mock_sess = MagicMock()
            mock_sess.exec.side_effect = Exception("DB unavailable")
            mock_session.return_value = iter([mock_sess])

            response = client.get("/biomarkers/panels")
            assert response.status_code == 200
            assert response.json() == []

    def test_list_panels_with_data(self, client):
        """GET /biomarkers/panels should return panel list."""
        mock_panel = MagicMock()
        mock_panel.id = 1
        mock_panel.target = "MSI"
        mock_panel.modality = "proteomics"
        mock_panel.features = [{"name": "GENE1"}, {"name": "GENE2"}]
        mock_panel.created_at = datetime.now(UTC)
        mock_panel.analysis_run_id = 10

        with patch("api.routes.biomarkers.get_session") as mock_session:
            mock_sess = MagicMock()
            mock_sess.exec.return_value.all.return_value = [mock_panel]
            mock_session.return_value = iter([mock_sess])

            response = client.get("/biomarkers/panels")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["target"] == "MSI"
            assert data[0]["n_features"] == 2

    def test_get_panel_features_not_found(self, client):
        """GET /biomarkers/{id}/features should 404 for missing panel."""
        with patch("api.routes.biomarkers.get_session") as mock_session:
            mock_sess = MagicMock()
            mock_sess.get.return_value = None
            mock_session.return_value = iter([mock_sess])

            response = client.get("/biomarkers/999/features")
            assert response.status_code == 404

    def test_get_panel_features_found(self, client):
        """GET /biomarkers/{id}/features should return panel details."""
        mock_panel = MagicMock()
        mock_panel.id = 1
        mock_panel.target = "MSI"
        mock_panel.modality = "proteomics"
        mock_panel.features = [{"name": "TAP1", "importance": 0.5}]
        mock_panel.method_agreement = {"TAP1": 2}
        mock_panel.analysis_run_id = 10
        mock_panel.created_at = datetime.now(UTC)

        with patch("api.routes.biomarkers.get_session") as mock_session:
            mock_sess = MagicMock()
            mock_sess.get.return_value = mock_panel
            mock_session.return_value = iter([mock_sess])

            response = client.get("/biomarkers/1/features")
            assert response.status_code == 200
            data = response.json()
            assert data["target"] == "MSI"
            assert len(data["features"]) == 1

    def test_get_panel_features_db_error(self, client):
        """GET /biomarkers/{id}/features should 503 on DB error."""
        with patch("api.routes.biomarkers.get_session") as mock_session:
            mock_sess = MagicMock()
            mock_sess.get.side_effect = Exception("Connection refused")
            mock_session.return_value = iter([mock_sess])

            response = client.get("/biomarkers/1/features")
            assert response.status_code == 503

    def test_panels_endpoint_returns_list(self, client):
        """GET /biomarkers/panels always returns a list."""
        with patch("api.routes.biomarkers.get_session") as mock_session:
            mock_sess = MagicMock()
            mock_sess.exec.return_value.all.return_value = []
            mock_session.return_value = iter([mock_sess])

            response = client.get("/biomarkers/panels")
            assert response.status_code == 200
            assert isinstance(response.json(), list)
