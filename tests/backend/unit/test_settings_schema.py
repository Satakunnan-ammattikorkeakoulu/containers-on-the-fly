"""Tests for settings_schema.py — schema definitions and validation logic."""

from helpers.settings_schema import (
    SETTINGS_SCHEMA,
    SettingSource,
    SettingType,
    get_setting_definition,
    get_file_settings,
    get_database_settings,
    get_required_settings,
    get_settings_by_prefix,
    validate_setting_value,
)


class TestSettingDefinitions:

    def test_required_file_settings_are_defined(self):
        required_keys = [
            "app.url", "app.serverIp", "app.clientUrl", "app.port",
            "database.engineUri", "docker.registryAddress", "docker.serverName",
        ]
        for key in required_keys:
            defn = get_setting_definition(key)
            assert defn is not None, f"Required setting {key} is not defined"
            assert defn.source == SettingSource.FILE
            assert defn.required is True

    def test_all_settings_have_valid_source(self):
        for key, defn in SETTINGS_SCHEMA.items():
            assert defn.source in (SettingSource.FILE, SettingSource.DATABASE), (
                f"Setting {key} has invalid source: {defn.source}"
            )

    def test_all_settings_have_valid_type(self):
        valid_types = set(SettingType)
        for key, defn in SETTINGS_SCHEMA.items():
            assert defn.data_type in valid_types, (
                f"Setting {key} has invalid type: {defn.data_type}"
            )

    def test_get_setting_definition_returns_none_for_unknown(self):
        assert get_setting_definition("nonexistent.key") is None

    def test_get_file_settings_returns_only_file(self):
        for key, defn in get_file_settings().items():
            assert defn.source == SettingSource.FILE

    def test_get_database_settings_returns_only_database(self):
        for key, defn in get_database_settings().items():
            assert defn.source == SettingSource.DATABASE

    def test_get_required_settings_all_required(self):
        for key, defn in get_required_settings().items():
            assert defn.required is True

    def test_get_settings_by_prefix(self):
        app_settings = get_settings_by_prefix("app.")
        assert len(app_settings) > 0
        for key in app_settings:
            assert key.startswith("app.")


class TestValidateSettingValue:

    def test_unknown_key_is_invalid(self):
        valid, msg = validate_setting_value("nonexistent", "value")
        assert valid is False
        assert "Unknown setting key" in msg

    def test_required_none_is_invalid(self):
        valid, msg = validate_setting_value("app.url", None)
        assert valid is False
        assert "cannot be None" in msg

    def test_optional_none_is_valid(self):
        valid, msg = validate_setting_value("app.logoUrl", None)
        assert valid is True

    def test_boolean_true_is_valid(self):
        valid, msg = validate_setting_value("app.production", True)
        assert valid is True

    def test_boolean_string_true_is_valid(self):
        valid, msg = validate_setting_value("app.production", "true")
        assert valid is True

    def test_boolean_invalid_string_is_invalid(self):
        valid, msg = validate_setting_value("app.production", "maybe")
        assert valid is False

    def test_integer_within_bounds(self):
        valid, msg = validate_setting_value("email.smtpPort", 587)
        assert valid is True

    def test_integer_below_min(self):
        valid, msg = validate_setting_value("email.smtpPort", 0)
        assert valid is False
        assert "at least" in msg

    def test_integer_above_max(self):
        valid, msg = validate_setting_value("email.smtpPort", 70000)
        assert valid is False
        assert "at most" in msg

    def test_integer_string_coercion(self):
        valid, msg = validate_setting_value("email.smtpPort", "587")
        assert valid is True

    def test_integer_non_numeric_string(self):
        valid, msg = validate_setting_value("email.smtpPort", "abc")
        assert valid is False

    def test_text_must_be_string(self):
        valid, msg = validate_setting_value("app.url", 123)
        assert valid is False

    def test_email_requires_at_sign(self):
        valid, msg = validate_setting_value("email.fromEmail", "notanemail")
        assert valid is False

    def test_email_valid(self):
        valid, msg = validate_setting_value("email.fromEmail", "test@example.com")
        assert valid is True

    def test_email_empty_is_valid(self):
        # Empty email should be valid (field is optional)
        valid, msg = validate_setting_value("email.fromEmail", "")
        assert valid is True

    def test_allowed_values_enforced(self):
        valid, msg = validate_setting_value("auth.loginType", "password")
        assert valid is True
        valid, msg = validate_setting_value("auth.loginType", "invalid")
        assert valid is False
        assert "must be one of" in msg
