"""General-purpose utility functions.

Provides helper functions for string sanitization and other common operations
used across the backend.
"""

import re

def remove_special_characters(string):
    """Remove all non-alphanumeric characters (except whitespace) from a string.

    Useful for sanitizing user input before using it in filesystem paths or
    other contexts where special characters could be problematic.

    Args:
        string: The input string to sanitize.

    Returns:
        The input string with all special characters removed, preserving
        only letters, digits, and whitespace.
    """
    pattern = re.compile(r'[^a-zA-Z0-9\s]')
    return re.sub(pattern, '', string) 