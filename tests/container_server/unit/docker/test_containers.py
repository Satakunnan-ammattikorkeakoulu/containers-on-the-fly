"""Unit tests for docker/containers.py — start, stop, restart operations."""

from unittest.mock import patch, MagicMock
import pytest
from docker.containers import start_container, stop_container, run_stop_script, restart_container


# Create a real exception class for NoSuchContainer since the conftest mocks
# the python_on_whales module globally and the mock attribute is not a real
# exception class.
class _NoSuchContainer(Exception):
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_params():
    """Minimal valid parameter dict for start_container."""
    return {
        "name": "test-container",
        "image": "ubuntu-base",
        "username": "user",
        "cpus": 4,
        "memory": "8g",
        "ports": [("2000", "22")],
        "dbUserId": "42",
        "reservation": {
            "computerId": 1,
            "user": {"email": "test@example.com"},
        },
        "roleMounts": [],
    }


# ---------------------------------------------------------------------------
# start_container
# ---------------------------------------------------------------------------

class TestStartContainer:

    @patch("docker.containers.inject_host_keys")
    @patch("docker.containers.run_user_config_script", return_value=None)
    @patch("docker.containers.build_volume_list", return_value=[])
    @patch("docker.containers.settings_handler")
    @patch("docker.containers.docker")
    def test_success(self, mock_docker, mock_settings, mock_volumes,
                     mock_config_script, mock_host_keys, base_params):
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_docker.run.return_value = mock_container
        mock_settings.get_setting.return_value = "localhost:5000"

        result = start_container(base_params)

        assert result["started"] is True
        assert result["containerName"] == "test-container"
        assert isinstance(result["password"], str)
        assert len(result["password"]) > 0
        assert result["error"] == ""
        assert result["containerId"] == "abc123"
        mock_docker.run.assert_called_once()
        mock_docker.execute.assert_called_once()  # password command

    @patch("docker.containers.inject_host_keys")
    @patch("docker.containers.run_user_config_script", return_value=None)
    @patch("docker.containers.build_volume_list", return_value=[])
    @patch("docker.containers.settings_handler")
    @patch("docker.containers.docker")
    def test_custom_password(self, mock_docker, mock_settings, mock_volumes,
                             mock_config_script, mock_host_keys, base_params):
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_docker.run.return_value = mock_container
        mock_settings.get_setting.return_value = "localhost:5000"

        base_params["password"] = "mypassword"
        result = start_container(base_params)
        assert result["password"] == "mypassword"

    @patch("docker.containers.inject_host_keys")
    @patch("docker.containers.run_user_config_script", return_value=None)
    @patch("docker.containers.build_volume_list", return_value=[])
    @patch("docker.containers.settings_handler")
    @patch("docker.containers.docker")
    def test_gpu_allocation(self, mock_docker, mock_settings, mock_volumes,
                            mock_config_script, mock_host_keys, base_params):
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_docker.run.return_value = mock_container
        mock_settings.get_setting.side_effect = lambda key: {
            "docker.registryAddress": "localhost:5000",
            "docker.debugSkipGpuDedication": False,
            "docker.sshHostKeysPath": "/tmp/keys",
        }.get(key)

        base_params["gpus"] = "device=0,1"
        result = start_container(base_params)
        assert result["started"] is True
        run_kwargs = mock_docker.run.call_args[1]
        assert "gpus" in run_kwargs

    @patch("docker.containers.inject_host_keys")
    @patch("docker.containers.run_user_config_script", return_value=None)
    @patch("docker.containers.build_volume_list", return_value=[])
    @patch("docker.containers.settings_handler")
    @patch("docker.containers.docker")
    def test_shm_size_calculation(self, mock_docker, mock_settings, mock_volumes,
                                  mock_config_script, mock_host_keys, base_params):
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_docker.run.return_value = mock_container
        mock_settings.get_setting.return_value = "localhost:5000"

        base_params["shm_size_percent"] = 25
        start_container(base_params)
        run_kwargs = mock_docker.run.call_args[1]
        # 8g = 8192MB, 25% = 2048MB
        assert run_kwargs["shm_size"] == "2048m"

    @patch("docker.containers.inject_host_keys")
    @patch("docker.containers.run_user_config_script", return_value=None)
    @patch("docker.containers.build_volume_list", return_value=[])
    @patch("docker.containers.settings_handler")
    @patch("docker.containers.docker")
    def test_ram_disk(self, mock_docker, mock_settings, mock_volumes,
                      mock_config_script, mock_host_keys, base_params):
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_docker.run.return_value = mock_container
        mock_settings.get_setting.return_value = "localhost:5000"

        base_params["ram_disk_percent"] = 10
        start_container(base_params)
        run_kwargs = mock_docker.run.call_args[1]
        assert "mounts" in run_kwargs

    @patch("docker.containers.inject_host_keys")
    @patch("docker.containers.run_user_config_script", return_value=None)
    @patch("docker.containers.build_volume_list", return_value=[])
    @patch("docker.containers.settings_handler")
    @patch("docker.containers.docker")
    def test_cleanup_on_docker_run_failure(self, mock_docker, mock_settings,
                                           mock_volumes, mock_config_script,
                                           mock_host_keys, base_params):
        mock_settings.get_setting.return_value = "localhost:5000"
        mock_docker.run.side_effect = RuntimeError("Docker daemon unreachable")

        result = start_container(base_params)
        assert result["started"] is False
        # Should attempt to stop the partially-created container
        mock_docker.stop.assert_called_once()

    @patch("docker.containers.inject_host_keys")
    @patch("docker.containers.run_user_config_script", return_value=None)
    @patch("docker.containers.build_volume_list", return_value=[])
    @patch("docker.containers.settings_handler")
    @patch("docker.containers.docker")
    def test_ssh_key_deployment(self, mock_docker, mock_settings, mock_volumes,
                                mock_config_script, mock_host_keys, base_params):
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_docker.run.return_value = mock_container
        mock_settings.get_setting.return_value = "localhost:5000"

        base_params["sshPublicKey"] = "ssh-rsa AAAA... user@host"
        result = start_container(base_params)
        assert result["started"] is True
        # Password + SSH key = 2 execute calls
        assert mock_docker.execute.call_count == 2

    @patch("docker.containers.inject_host_keys")
    @patch("docker.containers.run_user_config_script", return_value=None)
    @patch("docker.containers.build_volume_list", return_value=[])
    @patch("docker.containers.settings_handler")
    @patch("docker.containers.docker")
    def test_memory_unit_megabytes(self, mock_docker, mock_settings, mock_volumes,
                                   mock_config_script, mock_host_keys, base_params):
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_docker.run.return_value = mock_container
        mock_settings.get_setting.return_value = "localhost:5000"

        base_params["memory"] = "512m"
        start_container(base_params)
        run_kwargs = mock_docker.run.call_args[1]
        # 512MB, 50% default = 256MB
        assert run_kwargs["shm_size"] == "256m"

    @patch("docker.containers.inject_host_keys")
    @patch("docker.containers.run_user_config_script", return_value=None)
    @patch("docker.containers.build_volume_list", return_value=[])
    @patch("docker.containers.settings_handler")
    @patch("docker.containers.docker")
    def test_shm_percent_clamped_min(self, mock_docker, mock_settings, mock_volumes,
                                     mock_config_script, mock_host_keys, base_params):
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_docker.run.return_value = mock_container
        mock_settings.get_setting.return_value = "localhost:5000"

        base_params["shm_size_percent"] = 1  # below minimum 10
        start_container(base_params)
        run_kwargs = mock_docker.run.call_args[1]
        # 8g = 8192MB, clamped to 10% = 819MB
        assert run_kwargs["shm_size"] == "819m"

    @patch("docker.containers.inject_host_keys")
    @patch("docker.containers.run_user_config_script", return_value=None)
    @patch("docker.containers.build_volume_list", return_value=[])
    @patch("docker.containers.settings_handler")
    @patch("docker.containers.docker")
    def test_no_gpus_when_zero(self, mock_docker, mock_settings, mock_volumes,
                               mock_config_script, mock_host_keys, base_params):
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_docker.run.return_value = mock_container
        mock_settings.get_setting.return_value = "localhost:5000"

        base_params["gpus"] = 0
        start_container(base_params)
        run_kwargs = mock_docker.run.call_args[1]
        assert "gpus" not in run_kwargs

    @patch("docker.containers.inject_host_keys")
    @patch("docker.containers.run_user_config_script", return_value=None)
    @patch("docker.containers.build_volume_list", return_value=[])
    @patch("docker.containers.settings_handler")
    @patch("docker.containers.docker")
    def test_start_script_execution(self, mock_docker, mock_settings, mock_volumes,
                                    mock_config_script, mock_host_keys, base_params):
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_docker.run.return_value = mock_container
        mock_settings.get_setting.return_value = "localhost:5000"

        base_params["startScriptPath"] = "/opt/init.sh"
        result = start_container(base_params)
        assert result["started"] is True
        # password + start script = 2 execute calls
        assert mock_docker.execute.call_count == 2


# ---------------------------------------------------------------------------
# stop_container
# ---------------------------------------------------------------------------

class TestStopContainer:

    @patch("docker.containers.docker")
    def test_success(self, mock_docker):
        result = stop_container("my-container")
        assert result is True
        mock_docker.stop.assert_called_once_with("my-container", time=60)
        mock_docker.remove.assert_called_once_with("my-container")

    @patch("docker.containers.NoSuchContainer", new=_NoSuchContainer)
    @patch("docker.containers.docker")
    def test_not_found_on_stop(self, mock_docker):
        mock_docker.stop.side_effect = _NoSuchContainer("not found")
        result = stop_container("my-container")
        assert result is False
        # Still tries to remove even if stop fails
        mock_docker.remove.assert_called_once()

    @patch("docker.containers.NoSuchContainer", new=_NoSuchContainer)
    @patch("docker.containers.docker")
    def test_not_found_on_remove(self, mock_docker):
        mock_docker.remove.side_effect = _NoSuchContainer("not found")
        result = stop_container("my-container")
        assert result is False

    @patch("docker.containers.NoSuchContainer", new=_NoSuchContainer)
    @patch("docker.containers.docker")
    def test_both_fail(self, mock_docker):
        mock_docker.stop.side_effect = _NoSuchContainer("not found")
        mock_docker.remove.side_effect = _NoSuchContainer("not found")
        result = stop_container("my-container")
        assert result is False


# ---------------------------------------------------------------------------
# run_stop_script
# ---------------------------------------------------------------------------

class TestRunStopScript:

    @patch("docker.containers.docker")
    def test_executes_script(self, mock_docker):
        run_stop_script("my-container", "/opt/stop.sh")
        mock_docker.execute.assert_called_once()
        args = mock_docker.execute.call_args
        assert args[1]["container"] == "my-container"
        assert args[1]["user"] == "user"

    @patch("docker.containers.docker")
    def test_custom_username(self, mock_docker):
        run_stop_script("my-container", "/opt/stop.sh", container_username="admin")
        args = mock_docker.execute.call_args
        assert args[1]["user"] == "admin"

    @patch("docker.containers.docker")
    def test_empty_path_noop(self, mock_docker):
        run_stop_script("my-container", "")
        mock_docker.execute.assert_not_called()

    @patch("docker.containers.docker")
    def test_none_path_noop(self, mock_docker):
        run_stop_script("my-container", None)
        mock_docker.execute.assert_not_called()

    @patch("docker.containers.docker")
    def test_error_does_not_raise(self, mock_docker):
        mock_docker.execute.side_effect = RuntimeError("container gone")
        run_stop_script("my-container", "/opt/stop.sh")  # should not raise


# ---------------------------------------------------------------------------
# restart_container
# ---------------------------------------------------------------------------

class TestRestartContainer:

    @patch("docker.containers.docker")
    def test_success(self, mock_docker):
        restart_container("my-container")
        mock_docker.restart.assert_called_once_with("my-container", time=60)

    @patch("docker.containers.docker")
    def test_failure_raises(self, mock_docker):
        mock_docker.restart.side_effect = RuntimeError("cannot restart")
        with pytest.raises(RuntimeError):
            restart_container("my-container")
