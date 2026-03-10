"""Tests for API middleware."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


class TestAuditMiddleware:
    def test_request_id_header(self, client):
        response = client.get("/biomarkers/panels")
        assert "x-request-id" in response.headers

    def test_health_excluded(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert "x-request-id" not in response.headers


class TestAuthMiddleware:
    def test_no_auth_required_by_default(self, client):
        response = client.get("/biomarkers/panels")
        assert response.status_code == 200

    def test_auth_required_missing_key(self):
        with patch("core.config.get_settings") as mock_settings, \
             patch("api.middleware.auth.get_settings", mock_settings):
            settings = mock_settings.return_value
            settings.app_name = "Test"
            settings.environment = "test"
            settings.debug = False
            settings.require_auth = True
            settings.api_keys = "test-key-123"
            settings.enable_feature_store = False
            app = create_app()
            test_client = TestClient(app)
            response = test_client.get("/biomarkers/panels")
            assert response.status_code == 401

    def test_auth_required_valid_key(self):
        with patch("core.config.get_settings") as mock_settings, \
             patch("api.middleware.auth.get_settings", mock_settings):
            settings = mock_settings.return_value
            settings.app_name = "Test"
            settings.environment = "test"
            settings.debug = False
            settings.require_auth = True
            settings.api_keys = "test-key-123"
            settings.enable_feature_store = False
            app = create_app()
            test_client = TestClient(app)
            response = test_client.get(
                "/biomarkers/panels",
                headers={"X-API-Key": "test-key-123"},
            )
            assert response.status_code == 200

    def test_auth_required_invalid_key(self):
        with patch("core.config.get_settings") as mock_settings, \
             patch("api.middleware.auth.get_settings", mock_settings):
            settings = mock_settings.return_value
            settings.app_name = "Test"
            settings.environment = "test"
            settings.debug = False
            settings.require_auth = True
            settings.api_keys = "test-key-123"
            settings.enable_feature_store = False
            app = create_app()
            test_client = TestClient(app)
            response = test_client.get(
                "/biomarkers/panels",
                headers={"X-API-Key": "wrong-key"},
            )
            assert response.status_code == 403

    def test_skip_paths_bypass_auth(self):
        with patch("core.config.get_settings") as mock_settings, \
             patch("api.middleware.auth.get_settings", mock_settings):
            settings = mock_settings.return_value
            settings.app_name = "Test"
            settings.environment = "test"
            settings.debug = False
            settings.require_auth = True
            settings.api_keys = "test-key-123"
            settings.enable_feature_store = False
            app = create_app()
            test_client = TestClient(app)
            response = test_client.get("/health")
            assert response.status_code == 200

    def test_root_bypasses_auth(self):
        with patch("core.config.get_settings") as mock_settings, \
             patch("api.middleware.auth.get_settings", mock_settings):
            settings = mock_settings.return_value
            settings.app_name = "Test"
            settings.environment = "test"
            settings.debug = False
            settings.require_auth = True
            settings.api_keys = "test-key-123"
            settings.enable_feature_store = False
            app = create_app()
            test_client = TestClient(app)
            response = test_client.get("/")
            assert response.status_code == 200
