"""Tests for container server docker/ssh_host_keys.py."""

import os
from unittest.mock import patch, MagicMock, call
from docker.ssh_host_keys import ensure_host_keys, get_host_keys, inject_host_keys, _KEY_TYPES


class TestGetHostKeys:

    def test_returns_empty_for_nonexistent_directory(self, tmp_path):
        result = get_host_keys(str(tmp_path / "nonexistent"))
        assert result == {}

    def test_reads_key_files(self, tmp_path):
        keys_dir = tmp_path / "keys"
        keys_dir.mkdir()
        # Create a key pair
        (keys_dir / "ssh_host_rsa_key").write_text("PRIVATE_KEY_CONTENT")
        (keys_dir / "ssh_host_rsa_key.pub").write_text("PUBLIC_KEY_CONTENT")
        result = get_host_keys(str(keys_dir))
        assert result["ssh_host_rsa_key"] == "PRIVATE_KEY_CONTENT"
        assert result["ssh_host_rsa_key.pub"] == "PUBLIC_KEY_CONTENT"

    def test_reads_all_key_types(self, tmp_path):
        keys_dir = tmp_path / "keys"
        keys_dir.mkdir()
        for filename in _KEY_TYPES:
            (keys_dir / filename).write_text(f"private-{filename}")
            (keys_dir / f"{filename}.pub").write_text(f"public-{filename}")
        result = get_host_keys(str(keys_dir))
        assert len(result) == len(_KEY_TYPES) * 2

    def test_missing_keys_skipped(self, tmp_path):
        keys_dir = tmp_path / "keys"
        keys_dir.mkdir()
        # Only create one key type
        (keys_dir / "ssh_host_rsa_key").write_text("RSA_PRIVATE")
        result = get_host_keys(str(keys_dir))
        assert "ssh_host_rsa_key" in result
        assert "ssh_host_ecdsa_key" not in result


class TestEnsureHostKeys:

    @patch("docker.ssh_host_keys.subprocess.run")
    @patch("docker.ssh_host_keys.os.chmod")
    def test_generates_keys_when_missing(self, mock_chmod, mock_run, tmp_path):
        keys_dir = tmp_path / "keys"
        ensure_host_keys(str(keys_dir))
        # Should generate 3 key types
        assert mock_run.call_count == len(_KEY_TYPES)
        assert mock_chmod.call_count == len(_KEY_TYPES)

    @patch("docker.ssh_host_keys.subprocess.run")
    @patch("docker.ssh_host_keys.os.chmod")
    def test_skips_existing_keys(self, mock_chmod, mock_run, tmp_path):
        keys_dir = tmp_path / "keys"
        keys_dir.mkdir()
        # Create all key files
        for filename in _KEY_TYPES:
            (keys_dir / filename).write_text("existing")
        ensure_host_keys(str(keys_dir))
        # Should not generate any keys
        assert mock_run.call_count == 0

    @patch("docker.ssh_host_keys.subprocess.run")
    @patch("docker.ssh_host_keys.os.chmod")
    def test_generates_only_missing_keys(self, mock_chmod, mock_run, tmp_path):
        keys_dir = tmp_path / "keys"
        keys_dir.mkdir()
        # Create only RSA key
        (keys_dir / "ssh_host_rsa_key").write_text("existing")
        ensure_host_keys(str(keys_dir))
        # Should generate 2 keys (ecdsa and ed25519)
        assert mock_run.call_count == 2


class TestInjectHostKeys:

    @patch("docker.ssh_host_keys.docker")
    @patch("docker.ssh_host_keys.get_host_keys")
    def test_injects_all_keys(self, mock_get_keys, mock_docker):
        mock_get_keys.return_value = {
            "ssh_host_rsa_key": "RSA_PRIVATE",
            "ssh_host_rsa_key.pub": "RSA_PUBLIC",
            "ssh_host_ecdsa_key": "ECDSA_PRIVATE",
        }
        inject_host_keys("reservation-1", "/keys")
        # 3 key injections + 1 sshd reload = 4 calls
        assert mock_docker.execute.call_count == 4

    @patch("docker.ssh_host_keys.docker")
    @patch("docker.ssh_host_keys.get_host_keys")
    def test_correct_permissions(self, mock_get_keys, mock_docker):
        mock_get_keys.return_value = {
            "ssh_host_rsa_key": "PRIVATE",
            "ssh_host_rsa_key.pub": "PUBLIC",
        }
        inject_host_keys("reservation-1", "/keys")
        calls = mock_docker.execute.call_args_list
        # Find the private key injection (contains chmod 600)
        private_calls = [c for c in calls if "chmod 600" in str(c)]
        public_calls = [c for c in calls if "chmod 644" in str(c)]
        assert len(private_calls) == 1
        assert len(public_calls) == 1

    @patch("docker.ssh_host_keys.docker")
    @patch("docker.ssh_host_keys.get_host_keys")
    def test_skips_when_no_keys(self, mock_get_keys, mock_docker):
        mock_get_keys.return_value = {}
        inject_host_keys("reservation-1", "/keys")
        mock_docker.execute.assert_not_called()

    @patch("docker.ssh_host_keys.docker")
    @patch("docker.ssh_host_keys.get_host_keys")
    def test_handles_injection_error(self, mock_get_keys, mock_docker):
        mock_get_keys.return_value = {"ssh_host_rsa_key": "PRIVATE"}
        mock_docker.execute.side_effect = Exception("container not running")
        # Should not raise
        inject_host_keys("reservation-1", "/keys")
