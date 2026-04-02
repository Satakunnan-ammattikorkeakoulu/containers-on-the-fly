"""Simplified settings handler for the container server daemon.

Reads settings from a local settings.json file only. No database access,
no schema validation -- just file-based key-value access using dot notation.

Usage:
    from settings_handler import settings_handler, get_setting
    value = settings_handler.get_setting("docker.serverName")
"""

import json
import os
import re
from typing import Any


class ContainerServerSettings:
    """File-only settings handler for the container server daemon.

    Reads settings from settings.json using dot notation for nested keys.
    No database dependency.
    """

    def __init__(self, config_location: str = 'settings.json'):
        self._config_location = config_location
        self._file_settings = {}
        self._load_file_settings()

    def _load_file_settings(self):
        """Load settings from the settings.json file."""
        if not os.path.exists(self._config_location):
            raise RuntimeError(f"Settings file not found: {self._config_location}")

        with open(self._config_location, 'r') as handle:
            fixed_json = ''.join(line for line in handle if not re.match(r'^\s*//.*', line))
            self._file_settings = json.loads(fixed_json)

    def get_setting(self, key: str) -> Any:
        """Get a setting value by dot-notation key.

        Args:
            key: Setting key, e.g. 'docker.serverName' or 'daemon.apiKey'.

        Returns:
            The setting value, or None if not found.
        """
        keys = key.split('.')
        current = self._file_settings
        for k in keys:
            if not isinstance(current, dict) or k not in current:
                return None
            current = current[k]
        return current


settings_handler = ContainerServerSettings()


def get_setting(key: str) -> Any:
    """Global convenience function to get a setting."""
    return settings_handler.get_setting(key)
