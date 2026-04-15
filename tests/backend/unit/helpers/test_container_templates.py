"""Tests for helpers/container_templates.py."""

import io
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from helpers.container_templates import get_container_templates
from helpers.container_defaults import (
    DEFAULT_PASSWORD_COMMAND,
    DEFAULT_SSH_KEY_DEPLOY_COMMANDS,
)


def _make_template_json(**overrides):
    """Return a valid template dict, optionally overriding fields."""
    base = {
        "name": "Test Template",
        "baseImage": "ubuntu:22.04",
        "dockerfileBody": "RUN apt-get update",
        "containerCmd": '["/bin/bash"]',
    }
    base.update(overrides)
    return base


def _mock_file(data):
    """Return an open() context-manager mock that yields JSON text."""
    return io.StringIO(json.dumps(data))


class TestGetContainerTemplates:

    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_returns_empty_when_directory_missing(self, mock_dir):
        mock_dir.is_dir.return_value = False
        assert get_container_templates() == []

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_returns_sorted_list_with_valid_templates(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        file_a = Path("/fake/alpha.json")
        file_b = Path("/fake/beta.json")
        # sorted() expects comparable objects; real Path objects support <
        mock_dir.glob.return_value = [file_b, file_a]
        (mock_dir / "custom").is_dir.return_value = False

        templates_data = {
            file_a: _make_template_json(name="Alpha"),
            file_b: _make_template_json(name="Beta"),
        }
        mock_open.side_effect = lambda fp, *a, **kw: _mock_file(templates_data[fp])

        result = get_container_templates()
        assert len(result) == 2
        # Sorted by path: alpha.json < beta.json
        assert result[0]["name"] == "Alpha"
        assert result[1]["name"] == "Beta"
        assert all(
            key in result[0]
            for key in ("id", "name", "baseImage", "dockerfileBody", "containerCmd")
        )

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_skips_template_missing_required_fields(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        fp = MagicMock(spec=Path, stem="bad", name="bad.json")
        mock_dir.glob.return_value = [fp]
        (mock_dir / "custom").is_dir.return_value = False

        incomplete = {"name": "Missing baseImage"}
        mock_open.return_value = _mock_file(incomplete)

        assert get_container_templates() == []

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_skips_invalid_json(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        fp = MagicMock(spec=Path, stem="corrupt", name="corrupt.json")
        mock_dir.glob.return_value = [fp]
        (mock_dir / "custom").is_dir.return_value = False

        mock_open.return_value = io.StringIO("not valid json{{{")

        assert get_container_templates() == []

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_skips_file_on_os_error(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        fp = MagicMock(spec=Path, stem="locked", name="locked.json")
        mock_dir.glob.return_value = [fp]
        (mock_dir / "custom").is_dir.return_value = False

        mock_open.side_effect = OSError("Permission denied")

        assert get_container_templates() == []

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_interpolates_username_in_dockerfile_body(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        fp = MagicMock(spec=Path, stem="tpl", name="tpl.json")
        mock_dir.glob.return_value = [fp]
        (mock_dir / "custom").is_dir.return_value = False

        data = _make_template_json(dockerfileBody="RUN useradd {username}")
        mock_open.return_value = _mock_file(data)

        result = get_container_templates("student")
        assert "student" in result[0]["dockerfileBody"]
        assert "{username}" not in result[0]["dockerfileBody"]

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_default_username_is_user(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        fp = MagicMock(spec=Path, stem="tpl", name="tpl.json")
        mock_dir.glob.return_value = [fp]
        (mock_dir / "custom").is_dir.return_value = False

        mock_open.return_value = _mock_file(_make_template_json())

        result = get_container_templates()
        assert result[0]["containerUsername"] == "user"

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_uses_default_password_command_when_not_provided(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        fp = MagicMock(spec=Path, stem="tpl", name="tpl.json")
        mock_dir.glob.return_value = [fp]
        (mock_dir / "custom").is_dir.return_value = False

        mock_open.return_value = _mock_file(_make_template_json())

        result = get_container_templates()
        assert result[0]["passwordCommand"] == DEFAULT_PASSWORD_COMMAND

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_uses_default_ssh_deploy_when_not_provided(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        fp = MagicMock(spec=Path, stem="tpl", name="tpl.json")
        mock_dir.glob.return_value = [fp]
        (mock_dir / "custom").is_dir.return_value = False

        mock_open.return_value = _mock_file(_make_template_json())

        result = get_container_templates()
        assert result[0]["sshKeyDeployCommands"] == DEFAULT_SSH_KEY_DEPLOY_COMMANDS

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_uses_custom_password_command_when_provided(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        fp = MagicMock(spec=Path, stem="tpl", name="tpl.json")
        mock_dir.glob.return_value = [fp]
        (mock_dir / "custom").is_dir.return_value = False

        data = _make_template_json(passwordCommand="custom-cmd")
        mock_open.return_value = _mock_file(data)

        result = get_container_templates()
        assert result[0]["passwordCommand"] == "custom-cmd"

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_includes_custom_subdirectory_templates(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        root_fp = MagicMock(spec=Path, stem="root", name="root.json")
        mock_dir.glob.return_value = [root_fp]

        custom_dir = MagicMock()
        custom_dir.is_dir.return_value = True
        custom_fp = MagicMock(spec=Path, stem="custom_tpl", name="custom_tpl.json")
        custom_dir.glob.return_value = [custom_fp]
        mock_dir.__truediv__ = lambda self, key: custom_dir if key == "custom" else MagicMock()

        templates_data = {
            root_fp: _make_template_json(name="Root"),
            custom_fp: _make_template_json(name="Custom"),
        }
        mock_open.side_effect = lambda fp, *a, **kw: _mock_file(templates_data[fp])

        result = get_container_templates()
        assert len(result) == 2
        names = [t["name"] for t in result]
        assert "Root" in names
        assert "Custom" in names

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_id_is_filename_stem(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        fp = MagicMock(spec=Path, stem="my-template", name="my-template.json")
        mock_dir.glob.return_value = [fp]
        (mock_dir / "custom").is_dir.return_value = False

        mock_open.return_value = _mock_file(_make_template_json())

        result = get_container_templates()
        assert result[0]["id"] == "my-template"

    @patch("builtins.open")
    @patch("helpers.container_templates._TEMPLATES_DIR")
    def test_optional_fields_get_defaults(self, mock_dir, mock_open):
        mock_dir.is_dir.return_value = True
        fp = MagicMock(spec=Path, stem="tpl", name="tpl.json")
        mock_dir.glob.return_value = [fp]
        (mock_dir / "custom").is_dir.return_value = False

        mock_open.return_value = _mock_file(_make_template_json())

        result = get_container_templates()
        assert result[0]["description"] == ""
        assert result[0]["icon"] == "mdi-docker"
