"""Integration tests for /api/app endpoints."""


class TestGetPublicConfig:

    def test_no_auth_required(self, test_client):
        resp = test_client.get("/api/app/config")
        assert resp.status_code == 200

    def test_response_structure(self, test_client):
        resp = test_client.get("/api/app/config")
        data = resp.json()
        assert data["status"] is True
        assert "data" in data
        config = data["data"]
        assert "app" in config
        assert "name" in config["app"]
        assert "timezone" in config["app"]

    def test_returns_default_app_name(self, test_client):
        resp = test_client.get("/api/app/config")
        config = resp.json()["data"]
        # Default from settings_schema
        assert config["app"]["name"] == "Containers on the Fly"
