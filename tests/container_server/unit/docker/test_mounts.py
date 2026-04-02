"""Tests for container server docker/mounts.py."""

from unittest.mock import patch, MagicMock
from docker.mounts import (
    remove_special_characters,
    substitute_mount_variables,
    build_volume_list,
)


class TestRemoveSpecialCharacters:

    def test_removes_punctuation(self):
        assert remove_special_characters("hello!") == "hello"

    def test_preserves_spaces(self):
        assert remove_special_characters("hello world") == "hello world"

    def test_empty_string(self):
        assert remove_special_characters("") == ""

    def test_all_special_chars(self):
        assert remove_special_characters("@#$%^&*") == ""

    def test_preserves_numbers(self):
        assert remove_special_characters("test123") == "test123"

    def test_email_sanitization(self):
        assert remove_special_characters("user@foo.com") == "userfoocom"


class TestSubstituteMountVariables:

    def test_substitutes_email(self):
        result = substitute_mount_variables("/data/{email}", "user@foo.com", 1)
        assert result == "/data/userfoocom"

    def test_substitutes_userid(self):
        result = substitute_mount_variables("/data/{userid}", "user@foo.com", 42)
        assert result == "/data/42"

    def test_substitutes_both(self):
        result = substitute_mount_variables(
            "/data/{email}/{userid}", "user@foo.com", 42
        )
        assert result == "/data/userfoocom/42"

    def test_none_path_returns_none(self):
        assert substitute_mount_variables(None, "user@foo.com", 1) is None

    def test_empty_path_returns_empty(self):
        assert substitute_mount_variables("", "user@foo.com", 1) == ""

    def test_no_variables_unchanged(self):
        assert substitute_mount_variables("/data/fixed", "user@foo.com", 1) == "/data/fixed"


class TestBuildVolumeList:

    @patch("docker.mounts.prepare_mount_directory")
    def test_filters_by_computer_id(self, mock_prepare):
        mounts = [
            {"hostPath": "/data/a", "containerPath": "/mnt/a", "readOnly": False, "computerId": 1},
            {"hostPath": "/data/b", "containerPath": "/mnt/b", "readOnly": False, "computerId": 2},
        ]
        result = build_volume_list(mounts, 1, "user@foo.com", 1)
        assert len(result) == 1
        assert result[0] == ("/data/a", "/mnt/a")

    @patch("docker.mounts.prepare_mount_directory")
    def test_read_only_mount(self, mock_prepare):
        mounts = [
            {"hostPath": "/data/ro", "containerPath": "/mnt/ro", "readOnly": True, "computerId": 1},
        ]
        result = build_volume_list(mounts, 1, "user@foo.com", 1)
        assert result == [("/data/ro", "/mnt/ro", "ro")]

    @patch("docker.mounts.prepare_mount_directory")
    def test_read_write_mount(self, mock_prepare):
        mounts = [
            {"hostPath": "/data/rw", "containerPath": "/mnt/rw", "readOnly": False, "computerId": 1},
        ]
        result = build_volume_list(mounts, 1, "user@foo.com", 1)
        assert result == [("/data/rw", "/mnt/rw")]

    @patch("docker.mounts.prepare_mount_directory")
    def test_variable_substitution_in_paths(self, mock_prepare):
        mounts = [
            {"hostPath": "/data/{email}", "containerPath": "/home/{userid}", "readOnly": False, "computerId": 1},
        ]
        result = build_volume_list(mounts, 1, "user@foo.com", 42)
        assert result == [("/data/userfoocom", "/home/42")]

    @patch("docker.mounts.prepare_mount_directory")
    def test_empty_mounts_returns_empty(self, mock_prepare):
        assert build_volume_list([], 1, "user@foo.com", 1) == []

    @patch("docker.mounts.prepare_mount_directory")
    def test_calls_prepare_for_host_path(self, mock_prepare):
        mounts = [
            {"hostPath": "/data/test", "containerPath": "/mnt/test", "readOnly": False, "computerId": 1},
        ]
        build_volume_list(mounts, 1, "user@foo.com", 1)
        mock_prepare.assert_called_once_with("/data/test")
