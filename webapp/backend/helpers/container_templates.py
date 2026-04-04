"""File-based container image templates for the Image Builder.

Loads pre-made container templates from JSON files in the
``container_templates/`` directory at the project root. Each JSON file
defines a complete set of Image Builder fields that admins can use as a
starting point when creating new containers.

Templates can be shipped with the project (git-tracked) or added by users
by dropping new JSON files into the folder. The frontend also provides an
export button that downloads the current container config as a template
JSON file.
"""

import json
import os
from pathlib import Path

from helpers.container_defaults import (
    DEFAULT_CMD,
    DEFAULT_PASSWORD_COMMAND,
    DEFAULT_SSH_KEY_DEPLOY_COMMANDS,
)
from helpers.logger import log

# Resolve the container_templates/ directory relative to the project root.
# webapp/backend/helpers/container_templates.py -> project root is 3 levels up.
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "container_templates"

_REQUIRED_FIELDS = {"name", "baseImage", "dockerfileBody", "containerCmd"}


def get_container_templates(username="user"):
    """Load all container templates from the templates directory.

    Scans the ``container_templates/`` folder for ``.json`` files, validates
    required fields, interpolates ``{username}`` into text fields, and
    returns a sorted list of template dicts.

    Args:
        username: Linux username to interpolate into template fields.
            Replaces ``{username}`` placeholders in dockerfileBody,
            passwordCommand, and sshKeyDeployCommands.

    Returns:
        list[dict]: List of template dicts with camelCase keys, sorted by
        filename. Each dict contains: id, name, description, icon,
        baseImage, dockerfileBody, containerCmd, passwordCommand,
        sshKeyDeployCommands.
    """
    if not _TEMPLATES_DIR.is_dir():
        log.warning("Container templates directory not found: %s", _TEMPLATES_DIR)
        return []

    templates = []
    for filepath in sorted(_TEMPLATES_DIR.glob("*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Skipping invalid template file %s: %s", filepath.name, e)
            continue

        # Validate required fields
        missing = _REQUIRED_FIELDS - set(data.keys())
        if missing:
            log.warning(
                "Skipping template %s: missing required fields: %s",
                filepath.name,
                ", ".join(sorted(missing)),
            )
            continue

        # Build template dict with defaults for optional fields
        template = {
            "id": filepath.stem,
            "name": data["name"],
            "description": data.get("description", ""),
            "icon": data.get("icon", "mdi-docker"),
            "baseImage": data["baseImage"],
            "containerUsername": username,
            "dockerfileBody": data["dockerfileBody"].replace("{username}", username),
            "containerCmd": data["containerCmd"],
            "passwordCommand": data.get("passwordCommand", DEFAULT_PASSWORD_COMMAND),
            "sshKeyDeployCommands": data.get("sshKeyDeployCommands", DEFAULT_SSH_KEY_DEPLOY_COMMANDS),
        }

        templates.append(template)

    return templates
