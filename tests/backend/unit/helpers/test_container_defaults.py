"""Tests for helpers/container_defaults.py."""

from helpers.container_defaults import (
    get_default_dockerfile_body,
    DEFAULT_CMD,
    DEFAULT_PASSWORD_COMMAND,
    DEFAULT_SSH_KEY_DEPLOY_COMMANDS,
)


class TestGetDefaultDockerfileBody:

    def test_default_username(self):
        body = get_default_dockerfile_body()
        assert "useradd" in body
        assert "/home/user" in body
        assert "containerfly" in body

    def test_custom_username(self):
        body = get_default_dockerfile_body("student")
        assert "/home/student" in body
        assert "'student:password'" in body

    def test_contains_ssh_config(self):
        body = get_default_dockerfile_body()
        assert "openssh-server" in body
        assert "EXPOSE 22" in body

    def test_contains_containerfly_group(self):
        body = get_default_dockerfile_body()
        assert "groupadd -g 5620 containerfly" in body


class TestConstants:

    def test_default_cmd(self):
        assert "sshd" in DEFAULT_CMD
        assert DEFAULT_CMD.startswith("[")

    def test_password_command_placeholders(self):
        assert "{username}" in DEFAULT_PASSWORD_COMMAND
        assert "{password}" in DEFAULT_PASSWORD_COMMAND

    def test_ssh_deploy_placeholders(self):
        assert "{username}" in DEFAULT_SSH_KEY_DEPLOY_COMMANDS
        assert "{ssh_key}" in DEFAULT_SSH_KEY_DEPLOY_COMMANDS
        assert "authorized_keys" in DEFAULT_SSH_KEY_DEPLOY_COMMANDS
