"""Persistent SSH host key management for container servers.

Generates a single set of SSH host keys per container server and injects
them into every started container. This prevents SSH known_hosts conflicts
when different containers are assigned the same port — the host key stays
consistent across all containers on the server.
"""

import os
import re
import secrets
import subprocess
import traceback

from python_on_whales import docker
from helpers.logger import log

# Only allow standard SSH host key filenames to prevent path traversal
_VALID_HOST_KEY_RE = re.compile(r'^ssh_host_[a-z0-9_]+_key(\.pub)?$')


# Key types to generate, matching standard openssh-server defaults
_KEY_TYPES = {
    "ssh_host_rsa_key": "rsa",
    "ssh_host_ecdsa_key": "ecdsa",
    "ssh_host_ed25519_key": "ed25519",
}


def ensure_host_keys(keys_path):
    """Generate SSH host keys if they don't already exist.

    Creates RSA, ECDSA, and ED25519 key pairs in the given directory.
    Idempotent — existing keys are never overwritten.

    Args:
        keys_path: Directory where host keys are stored.
    """
    os.makedirs(keys_path, exist_ok=True)

    for filename, key_type in _KEY_TYPES.items():
        key_file = os.path.join(keys_path, filename)
        if os.path.exists(key_file):
            continue

        try:
            subprocess.run(
                ["ssh-keygen", "-t", key_type, "-f", key_file, "-N", "", "-q"],
                check=True,
            )
            os.chmod(key_file, 0o600)
            log.info(f"Generated SSH host key: {key_file}")
        except Exception as e:
            log.error(f"Error generating SSH host key {key_file}: {e}")


def get_host_keys(keys_path):
    """Read all host key files (private + public) from the given directory.

    Args:
        keys_path: Directory containing the host key files.

    Returns:
        dict: Mapping of filename to file content, e.g.
            {"ssh_host_rsa_key": "-----BEGIN...", "ssh_host_rsa_key.pub": "ssh-rsa ..."}
            Returns empty dict if the directory does not exist.
    """
    if not os.path.isdir(keys_path):
        return {}

    keys = {}
    for filename in _KEY_TYPES:
        for suffix in ("", ".pub"):
            full_name = filename + suffix
            path = os.path.join(keys_path, full_name)
            if os.path.exists(path):
                with open(path, "r") as f:
                    keys[full_name] = f.read()
    return keys


def inject_host_keys(container_name, keys_path):
    """Inject persistent SSH host keys into a running container.

    Overwrites the container's auto-generated host keys in /etc/ssh/ with
    the server-wide keys, then signals sshd to reload. This is non-critical:
    failures are logged but do not propagate.

    Args:
        container_name: Docker container name to inject keys into.
        keys_path: Directory containing the host key files.
    """
    try:
        keys = get_host_keys(keys_path)
        if not keys:
            log.warning(f"No SSH host keys found at {keys_path}, skipping injection for {container_name}")
            return

        for filename, content in keys.items():
            # Validate filename to prevent path traversal
            if not _VALID_HOST_KEY_RE.match(filename):
                log.warning(f"Skipping invalid SSH host key filename: {filename}")
                continue

            # Determine correct permissions: private keys 600, public keys 644
            is_private = not filename.endswith(".pub")
            chmod = "600" if is_private else "644"

            # Use heredoc with a randomized delimiter to prevent injection
            # via key content that contains the delimiter string
            delimiter = f"HOSTKEY_EOF_{secrets.token_hex(8)}"
            inject_cmd = (
                f"cat > /etc/ssh/{filename} << '{delimiter}'\n"
                f"{content}"
                f"{delimiter}\n"
                f"chmod {chmod} /etc/ssh/{filename}"
            )
            docker.execute(
                container=container_name,
                command=["/bin/bash", "-c", inject_cmd],
                user="root",
            )

        # Reload sshd to pick up the new keys
        docker.execute(
            container=container_name,
            command=["/bin/bash", "-c", "pkill -HUP sshd 2>/dev/null || true"],
            user="root",
        )
    except Exception as e:
        log.warning(f"Non-critical error injecting SSH host keys into {container_name}: {e}\n{traceback.format_exc()}")
