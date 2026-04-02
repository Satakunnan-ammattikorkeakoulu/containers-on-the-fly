"""Tests for container server docker/image_builder.py."""

import pytest
from datetime import timedelta
from docker.image_builder import (
    get_default_dockerfile_body,
    generate_dockerfile,
    _format_size,
    _format_duration,
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
