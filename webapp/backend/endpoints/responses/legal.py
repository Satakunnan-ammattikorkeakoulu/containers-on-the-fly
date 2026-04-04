"""Response handlers for public legal document endpoints.

Retrieves privacy policy and terms of service content from database
settings and returns them for unauthenticated display.
"""

from helpers.server import api_response
from helpers.logger import log


def get_privacy_policy() -> object:
    """Return privacy policy content if legal documents are enabled.

    Checks the legal.enabled setting and returns the privacy policy
    Markdown content along with organization name and contact email.

    Returns:
        Response with privacy policy content, or error if disabled.
    """
    try:
        from helpers.settings_handler import get_multiple_settings

        setting_keys = [
            'legal.enabled',
            'legal.privacyPolicyContent',
            'legal.organizationName',
            'legal.contactEmail',
            'legal.lastUpdated'
        ]

        settings_dict = get_multiple_settings(setting_keys)

        if not settings_dict.get('legal.enabled', False):
            return api_response(False, "Legal documents are not enabled")

        return api_response(True, "Privacy policy retrieved", {
            "content": settings_dict.get('legal.privacyPolicyContent', ''),
            "organizationName": settings_dict.get('legal.organizationName', ''),
            "contactEmail": settings_dict.get('legal.contactEmail', ''),
            "lastUpdated": settings_dict.get('legal.lastUpdated', '')
        })

    except Exception as e:
        log.error(f"Error retrieving privacy policy: {str(e)}")
        return api_response(False, "Error retrieving privacy policy")


def get_terms_of_service() -> object:
    """Return terms of service content if legal documents are enabled.

    Checks the legal.enabled setting and returns the terms of service
    Markdown content along with organization name and contact email.

    Returns:
        Response with terms of service content, or error if disabled.
    """
    try:
        from helpers.settings_handler import get_multiple_settings

        setting_keys = [
            'legal.enabled',
            'legal.termsOfServiceContent',
            'legal.organizationName',
            'legal.contactEmail',
            'legal.lastUpdated'
        ]

        settings_dict = get_multiple_settings(setting_keys)

        if not settings_dict.get('legal.enabled', False):
            return api_response(False, "Legal documents are not enabled")

        return api_response(True, "Terms of service retrieved", {
            "content": settings_dict.get('legal.termsOfServiceContent', ''),
            "organizationName": settings_dict.get('legal.organizationName', ''),
            "contactEmail": settings_dict.get('legal.contactEmail', ''),
            "lastUpdated": settings_dict.get('legal.lastUpdated', '')
        })

    except Exception as e:
        log.error(f"Error retrieving terms of service: {str(e)}")
        return api_response(False, "Error retrieving terms of service")
