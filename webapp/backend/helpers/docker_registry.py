"""Docker Registry v2 HTTP API helpers.

Provides synchronous existence checks against the local Docker registry
so the backend can warn admins before silently overwriting an existing
image name during container creation.
"""

import re
from typing import Optional

import requests

from helpers.logger import log
from helpers.settings_handler import settings_handler

# Same pattern used for validating user-supplied image names elsewhere.
# Restricts the URL path component to a safe subset so the HTTP call
# cannot be manipulated into hitting a different endpoint.
_VALID_IMAGE_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._/\-]{0,127}$')


def image_exists_in_registry(image_name: str) -> Optional[bool]:
    """Check whether an image is present in the configured Docker registry.

    Issues a HEAD request against the registry's v2 manifests endpoint for
    the ``latest`` tag. The registry is considered unreachable / indeterminate
    on any non-200/404 response, in which case ``None`` is returned so
    callers can degrade gracefully instead of blocking the user.

    Args:
        image_name: Image name (without registry prefix or tag), e.g.
            ``my-container``. Must pass the same format validation as
            user-supplied image names.

    Returns:
        True if the registry has a ``latest`` manifest for ``image_name``,
        False if the registry returned 404, or None on any other condition
        (invalid name, timeout, network error, unexpected status code).
    """
    if not image_name or not _VALID_IMAGE_NAME_RE.match(image_name):
        return None

    registry_address = settings_handler.get_setting("docker.registryAddress")
    if not registry_address:
        return None
    scheme = settings_handler.get_setting("docker.registryScheme") or "http"

    url = f"{scheme}://{registry_address}/v2/{image_name}/manifests/latest"
    headers = {
        "Accept": (
            "application/vnd.docker.distribution.manifest.v2+json, "
            "application/vnd.oci.image.manifest.v1+json"
        ),
    }
    try:
        response = requests.head(url, headers=headers, timeout=(3, 5))
    except requests.RequestException as e:
        log.warning(f"Registry check failed for {image_name}: {e}")
        return None

    if response.status_code == 200:
        return True
    if response.status_code == 404:
        return False
    log.warning(
        f"Registry returned unexpected status {response.status_code} "
        f"for {image_name}, treating as unknown"
    )
    return None
