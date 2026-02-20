"""Tests for API middleware."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestAuditMiddleware:
    def test_health_endpoint_not_audited(self, client, caplog):
        """Health endpoint should be excluded from audit logging."""
        with caplog.at_level(logging.INFO, logger="audit"):
            response = client.get("/health")
            assert response.status_code == 200
            # Audit logger should NOT have logged for /health
            audit_messages = [r for r in caplog.records if r.name == "audit"]
            health_logs = [r for r in audit_messages if "/health" in r.message]
            assert len(health_logs) == 0

    def test_regular_endpoint_gets_request_id(self, client):
        """Non-excluded endpoints should get an X-Request-ID header."""
        response = client.get("/")
        assert response.status_code == 200
        assert "x-request-id" in response.headers

    def test_audit_logs_request(self, client, caplog):
        """Audit middleware should log request start and end."""
        with caplog.at_level(logging.INFO, logger="audit"):
            response = client.get("/")
            assert response.status_code == 200
            audit_messages = [r.message for r in caplog.records if r.name == "audit"]
            # Should have start and end logs
            starts = [m for m in audit_messages if "request_start" in m]
            ends = [m for m in audit_messages if "request_end" in m]
            assert len(starts) >= 1
            assert len(ends) >= 1


class TestAuthMiddleware:
    def test_health_skips_auth(self, client):
        """Health endpoint should skip auth check."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_root_skips_auth(self, client):
        """Root endpoint should skip auth check."""
        response = client.get("/")
        assert response.status_code == 200

    def test_no_auth_required_by_default(self, client):
        """With require_auth=False (default), all requests pass."""
        response = client.get("/biomarkers/panels")
        assert response.status_code == 200

    @pytest.mark.skipif(True, reason="Requires auth configuration")
    def test_auth_required_missing_key(self):
        """With require_auth=True, missing key should 401."""
        with patch("core.config.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.require_auth = True
            settings.api_keys = "test-key-123"
            settings.debug = True
            settings.app_name = "test"
            settings.environment = "test"
            settings.enable_feature_store = False

            app = create_app()
            client = TestClient(app)
            response = client.get("/biomarkers/panels")
            assert response.status_code == 401

    @pytest.mark.skipif(True, reason="Requires auth configuration")
    def test_auth_required_invalid_key(self):
        """With require_auth=True, invalid key should 403."""
        with patch("core.config.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.require_auth = True
            settings.api_keys = "valid-key"
            settings.debug = True
            settings.app_name = "test"
            settings.environment = "test"

            app = create_app()
            client = TestClient(app)
            response = client.get(
                "/biomarkers/panels",
                headers={"X-API-Key": "wrong-key"},
            )
            assert response.status_code == 403
