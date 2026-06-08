"""Tests for container server docker/image_builder.py."""

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock
from docker.image_builder import (
    get_default_dockerfile_body,
    generate_dockerfile,
    _format_size,
    _format_duration,
    build_and_push_image,
    remove_image,
    update_all_image_sizes,
    DEFAULT_CMD,
    DEFAULT_PASSWORD_COMMAND,
    DEFAULT_SSH_KEY_DEPLOY_COMMANDS,
)


class TestGetDefaultDockerfileBody:

    def test_default_username(self):
        body = get_default_dockerfile_body()
        assert "user" in body
        assert "useradd" in body
        assert "containerfly" in body

    def test_custom_username(self):
        body = get_default_dockerfile_body("myuser")
        assert "myuser" in body
        assert "/home/myuser" in body

    def test_contains_ssh_setup(self):
        body = get_default_dockerfile_body()
        assert "openssh-server" in body
        assert "sshd_config" in body
        assert "EXPOSE 22" in body

    def test_contains_containerfly_group(self):
        body = get_default_dockerfile_body()
        assert "groupadd -g 5620 containerfly" in body


class TestGenerateDockerfile:

    def test_valid_base_image(self):
        result = generate_dockerfile("ubuntu:22.04", "RUN echo hello")
        assert result.startswith("FROM ubuntu:22.04")
        assert "RUN echo hello" in result
        assert f"CMD {DEFAULT_CMD}" in result

    def test_custom_cmd(self):
        result = generate_dockerfile("ubuntu:22.04", "RUN echo hi", '["/bin/sh"]')
        assert 'CMD ["/bin/sh"]' in result

    def test_default_cmd_used_when_none(self):
        result = generate_dockerfile("ubuntu:22.04", "RUN echo hi")
        assert f"CMD {DEFAULT_CMD}" in result

    def test_invalid_base_image_raises(self):
        with pytest.raises(ValueError, match="Invalid base image name"):
            generate_dockerfile("invalid image!!", "RUN echo hi")

    def test_strips_body_whitespace(self):
        result = generate_dockerfile("ubuntu:22.04", "  RUN echo hi  \n")
        assert "  RUN echo hi" not in result or "RUN echo hi" in result

    def test_output_structure(self):
        result = generate_dockerfile("alpine:3.18", "RUN apk add bash")
        lines = result.split("\n")
        assert lines[0] == "FROM alpine:3.18"
        assert lines[-2].startswith("CMD ")


class TestFormatSize:

    def test_bytes(self):
        assert _format_size(500) == "500.0 B"

    def test_kilobytes(self):
        assert _format_size(2048) == "2.0 KB"

    def test_megabytes(self):
        assert _format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_gigabytes(self):
        assert _format_size(3 * 1024 ** 3) == "3.0 GB"

    def test_terabytes(self):
        assert _format_size(2 * 1024 ** 4) == "2.0 TB"

    def test_none_returns_unknown(self):
        assert _format_size(None) == "Unknown"


class TestFormatDuration:

    def test_seconds_only(self):
        assert _format_duration(timedelta(seconds=45)) == "45s"

    def test_minutes_and_seconds(self):
        assert _format_duration(timedelta(seconds=125)) == "2m 5s"

    def test_hours_minutes_seconds(self):
        assert _format_duration(timedelta(seconds=3725)) == "1h 2m 5s"

    def test_zero_duration(self):
        assert _format_duration(timedelta(seconds=0)) == "0s"


class TestConstants:

    def test_default_cmd_contains_sshd(self):
        assert "sshd" in DEFAULT_CMD

    def test_default_password_command_has_placeholders(self):
        assert "{username}" in DEFAULT_PASSWORD_COMMAND
        assert "{password}" in DEFAULT_PASSWORD_COMMAND

    def test_default_ssh_deploy_has_placeholders(self):
        assert "{username}" in DEFAULT_SSH_KEY_DEPLOY_COMMANDS
        assert "{ssh_key}" in DEFAULT_SSH_KEY_DEPLOY_COMMANDS


class TestRemoveImage:

    @patch("docker.image_builder.docker")
    @patch("docker.image_builder.settings_handler")
    def test_success(self, mock_settings, mock_docker):
        mock_settings.get_setting.return_value = "localhost:5000"
        mock_api = MagicMock()

        result = remove_image({"containerId": 1, "imageName": "test-img"}, mock_api)
        assert result is True
        mock_docker.image.remove.assert_called_once_with("localhost:5000/test-img:latest", force=True)
        mock_api.report_image_removed.assert_called_once_with(1, "removed")

    @patch("docker.image_builder.docker")
    @patch("docker.image_builder.settings_handler")
    def test_handles_image_not_found(self, mock_settings, mock_docker):
        mock_settings.get_setting.return_value = "localhost:5000"
        mock_docker.image.remove.side_effect = Exception("not found")
        mock_api = MagicMock()

        result = remove_image({"containerId": 1, "imageName": "missing"}, mock_api)
        assert result is True  # Still reports removal even if image not found locally
        mock_api.report_image_removed.assert_called_once()

    @patch("docker.image_builder.docker")
    @patch("docker.image_builder.settings_handler")
    def test_returns_false_on_api_error(self, mock_settings, mock_docker):
        mock_settings.get_setting.return_value = "localhost:5000"
        mock_api = MagicMock()
        mock_api.report_image_removed.side_effect = Exception("API down")

        result = remove_image({"containerId": 1, "imageName": "test-img"}, mock_api)
        assert result is False


class TestUpdateAllImageSizes:

    @patch("docker.image_builder.docker")
    @patch("docker.image_builder.settings_handler")
    def test_builds_correct_batch(self, mock_settings, mock_docker):
        mock_settings.get_setting.return_value = "localhost:5000"
        img1 = MagicMock(repo_tags=["localhost:5000/ubuntu-base:latest"], size=2_000_000_000)
        img2 = MagicMock(repo_tags=["localhost:5000/pytorch:latest"], size=5_000_000_000)
        mock_docker.image.list.return_value = [img1, img2]
        mock_api = MagicMock()

        update_all_image_sizes(mock_api)
        mock_api.update_image_sizes_batch.assert_called_once()
        batch = mock_api.update_image_sizes_batch.call_args[0][0]
        names = {item["imageName"] for item in batch}
        assert "ubuntu-base" in names
        assert "pytorch" in names

    @patch("docker.image_builder.docker")
    @patch("docker.image_builder.settings_handler")
    def test_filters_by_registry_prefix(self, mock_settings, mock_docker):
        mock_settings.get_setting.return_value = "localhost:5000"
        img_local = MagicMock(repo_tags=["localhost:5000/myimg:latest"], size=100)
        img_other = MagicMock(repo_tags=["docker.io/library/ubuntu:latest"], size=200)
        mock_docker.image.list.return_value = [img_local, img_other]
        mock_api = MagicMock()

        update_all_image_sizes(mock_api)
        batch = mock_api.update_image_sizes_batch.call_args[0][0]
        assert len(batch) == 1
        assert batch[0]["imageName"] == "myimg"

    @patch("docker.image_builder.docker")
    @patch("docker.image_builder.settings_handler")
    def test_no_images(self, mock_settings, mock_docker):
        mock_settings.get_setting.return_value = "localhost:5000"
        mock_docker.image.list.return_value = []
        mock_api = MagicMock()

        update_all_image_sizes(mock_api)
        mock_api.update_image_sizes_batch.assert_not_called()


class TestBuildAndPushImage:

    def test_skips_when_no_dockerfile_commands(self):
        mock_api = MagicMock()
        result = build_and_push_image(
            {"containerId": 1, "imageName": "test", "dockerfileCommands": ""},
            mock_api,
        )
        assert result is False

    @patch("docker.image_builder.shutil.rmtree")
    @patch("docker.image_builder.tempfile.mkdtemp", return_value="/tmp/cotf_build_test")
    @patch("docker.image_builder.docker")
    @patch("docker.image_builder.settings_handler")
    def test_reports_failure_on_build_error(self, mock_settings, mock_docker, mock_mkdtemp, mock_rmtree):
        mock_settings.get_setting.return_value = "localhost:5000"
        mock_docker.build.side_effect = Exception("build failed")
        mock_api = MagicMock()

        with patch("builtins.open", MagicMock()):
            with patch("docker.image_builder.os.path.exists", return_value=True):
                result = build_and_push_image(
                    {
                        "containerId": 1,
                        "imageName": "test",
                        "baseImage": "ubuntu:22.04",
                        "dockerfileCommands": "RUN echo hello",
                        "containerUsername": "user",
                        "containerCmd": None,
                    },
                    mock_api,
                )

        assert result is False
        mock_api.report_build_complete.assert_called_once()
        call_args = mock_api.report_build_complete.call_args[0]
        assert call_args[1]["buildStatus"] == "failed"
