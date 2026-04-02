"""Utility functions for the container server daemon."""

import secrets
import string


def create_password(length=40):
    """Generate a cryptographically secure random password.

    Args:
        length: The desired password length. Defaults to 40.

    Returns:
        A random string of ASCII letters and digits.
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))
