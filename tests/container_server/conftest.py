"""
Shared test configuration for container server tests.

Module-level setup:
  1. Adds webapp/container_server to sys.path
  2. Changes CWD to webapp/container_server so settings.json is found
  3. Patches settings_handler to use test_settings.json
  4. Mocks heavy external dependencies (python_on_whales, psutil)
"""

import sys
import os
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# 1. Path and CWD setup
# ---------------------------------------------------------------------------
_container_server_dir = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "webapp", "container_server")
)
if _container_server_dir not in sys.path:
    sys.path.insert(0, _container_server_dir)

_original_cwd = os.getcwd()
os.chdir(_container_server_dir)

# ---------------------------------------------------------------------------
# 2. Mock heavy system-level dependencies before any imports
# ---------------------------------------------------------------------------
# python_on_whales requires Docker to be installed
_mock_docker = MagicMock()
sys.modules["python_on_whales"] = MagicMock()
sys.modules["python_on_whales.docker"] = _mock_docker
sys.modules["python_on_whales.exceptions"] = MagicMock()

# psutil may not be installed in test environments
if "psutil" not in sys.modules:
    try:
        import psutil  # noqa: F401
    except ImportError:
        sys.modules["psutil"] = MagicMock()

# ---------------------------------------------------------------------------
# 3. Patch settings_handler to use test settings
# ---------------------------------------------------------------------------
import helpers.settings_handler as _sh_module

_test_settings_path = os.path.join(os.path.dirname(__file__), "test_settings.json")
_test_settings = _sh_module.ContainerServerSettings(config_location=_test_settings_path)

_sh_module.settings_handler = _test_settings
_sh_module.get_setting = _test_settings.get_setting
