"""Integration tests for /api/legal endpoints."""

import database as db
from sqlalchemy import select
from helpers.settings_handler import settings_handler


def _clear_settings_cache():
    """Invalidate the DB settings cache so changes take effect immediately."""
    settings_handler.clear_database_cache()


def _set_legal_settings(session, enabled=True, **kwargs):
    """Insert SystemSetting rows for legal settings."""
    settings = {
        "legal.enabled": str(enabled).lower(),
        "legal.privacyPolicyContent": kwargs.get("privacy", ""),
        "legal.termsOfServiceContent": kwargs.get("tos", ""),
        "legal.organizationName": kwargs.get("org", ""),
        "legal.contactEmail": kwargs.get("email", ""),
        "legal.lastUpdated": kwargs.get("last_updated", ""),
    }
    for key, value in settings.items():
        existing = session.execute(
            select(db.SystemSetting).where(db.SystemSetting.settingKey == key)
        ).scalar_one_or_none()
        if existing:
            existing.settingValue = value
        else:
            session.add(db.SystemSetting(
                settingKey=key,
                settingValue=value,
                dataType="boolean" if key == "legal.enabled" else "text",
            ))
    session.commit()
    _clear_settings_cache()


class TestPrivacyPolicy:

    def _clear_legal_settings(self):
        """Remove all legal settings to ensure test isolation."""
        with db.Session() as session:
            session.execute(
                db.SystemSetting.__table__.delete().where(
                    db.SystemSetting.settingKey.like("legal.%")
                )
            )
            session.commit()
        _clear_settings_cache()

    def test_returns_disabled_when_not_enabled(self, test_client):
        self._clear_legal_settings()
        resp = test_client.get("/api/legal/privacy-policy")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is False

    def test_returns_content_when_enabled(self, test_client):
        self._clear_legal_settings()
        with db.Session() as session:
            _set_legal_settings(
                session,
                enabled=True,
                privacy="# Privacy Policy\nWe care.",
                org="Acme Corp",
                email="legal@acme.com",
                last_updated="2025-01-01",
            )

        resp = test_client.get("/api/legal/privacy-policy")
        data = resp.json()
        assert data["status"] is True
        assert data["data"]["content"] == "# Privacy Policy\nWe care."
        assert data["data"]["organizationName"] == "Acme Corp"
        assert data["data"]["contactEmail"] == "legal@acme.com"
        assert data["data"]["lastUpdated"] == "2025-01-01"

    def test_returns_empty_strings_for_missing_content(self, test_client):
        self._clear_legal_settings()
        with db.Session() as session:
            _set_legal_settings(session, enabled=True)

        resp = test_client.get("/api/legal/privacy-policy")
        data = resp.json()
        assert data["status"] is True
        assert data["data"]["content"] == ""
        assert data["data"]["organizationName"] == ""

    def test_no_auth_required(self, test_client):
        resp = test_client.get("/api/legal/privacy-policy")
        assert resp.status_code == 200


class TestTermsOfService:

    def _clear_legal_settings(self):
        with db.Session() as session:
            session.execute(
                db.SystemSetting.__table__.delete().where(
                    db.SystemSetting.settingKey.like("legal.%")
                )
            )
            session.commit()

    def test_returns_disabled_when_not_enabled(self, test_client):
        self._clear_legal_settings()
        with db.Session() as session:
            _set_legal_settings(session, enabled=False)

        resp = test_client.get("/api/legal/terms-of-service")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is False

    def test_returns_content_when_enabled(self, test_client):
        self._clear_legal_settings()
        with db.Session() as session:
            _set_legal_settings(
                session,
                enabled=True,
                tos="# Terms\nUse responsibly.",
                org="Acme Corp",
                email="legal@acme.com",
                last_updated="2025-02-01",
            )

        resp = test_client.get("/api/legal/terms-of-service")
        data = resp.json()
        assert data["status"] is True
        assert data["data"]["content"] == "# Terms\nUse responsibly."
        assert data["data"]["organizationName"] == "Acme Corp"

    def test_returns_empty_strings_for_missing_content(self, test_client):
        self._clear_legal_settings()
        with db.Session() as session:
            _set_legal_settings(session, enabled=True)

        resp = test_client.get("/api/legal/terms-of-service")
        data = resp.json()
        assert data["status"] is True
        assert data["data"]["content"] == ""

    def test_no_auth_required(self, test_client):
        resp = test_client.get("/api/legal/terms-of-service")
        assert resp.status_code == 200
