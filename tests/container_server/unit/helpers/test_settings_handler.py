"""Tests for container server helpers/settings_handler.py."""

import json
import os
import tempfile

import pytest

from helpers.settings_handler import ContainerServerSettings


class TestContainerServerSettings:

    def test_loads_valid_settings_file(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"app": {"name": "test"}}))
        s = ContainerServerSettings(config_location=str(settings_file))
        assert s.get_setting("app.name") == "test"

    def test_raises_for_missing_file(self):
        with pytest.raises(RuntimeError, match="Settings file not found"):
            ContainerServerSettings(config_location="/nonexistent/path.json")

    def test_get_top_level_key(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"debug": True}))
        s = ContainerServerSettings(config_location=str(settings_file))
        assert s.get_setting("debug") is True

    def test_get_nested_key(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"docker": {"serverName": "srv1"}}))
        s = ContainerServerSettings(config_location=str(settings_file))
        assert s.get_setting("docker.serverName") == "srv1"

    def test_missing_key_returns_none(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"app": {}}))
        s = ContainerServerSettings(config_location=str(settings_file))
        assert s.get_setting("app.nonexistent") is None

    def test_missing_top_level_key_returns_none(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"app": {}}))
        s = ContainerServerSettings(config_location=str(settings_file))
        assert s.get_setting("nope") is None

    def test_handles_comment_lines(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        content = '// This is a comment\n{"app": {"name": "test"}}\n'
        settings_file.write_text(content)
        s = ContainerServerSettings(config_location=str(settings_file))
        assert s.get_setting("app.name") == "test"

    def test_deeply_nested_key(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"a": {"b": {"c": "deep"}}}))
        s = ContainerServerSettings(config_location=str(settings_file))
        assert s.get_setting("a.b.c") == "deep"

    def test_non_dict_traversal_returns_none(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"key": "string_value"}))
        s = ContainerServerSettings(config_location=str(settings_file))
        assert s.get_setting("key.child") is None
