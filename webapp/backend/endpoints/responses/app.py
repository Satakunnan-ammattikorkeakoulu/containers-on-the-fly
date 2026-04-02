"""Response handlers for public application endpoints.

Provides configuration data that is accessible without authentication,
such as application name, timezone, login instructions, and contact info.
"""

from helpers.server import api_response
from helpers.logger import log

def get_public_config() -> object:
    """Return public app configuration that does not require authentication.

    Retrieves application name, timezone, instruction messages, and contact
    information from database settings and returns them in a structured format
    for the frontend login and reservation pages.

    Returns:
        Response object with public configuration data including app info,
        instruction texts, and login field labels.
    """
    try:
        from helpers.settings_handler import get_multiple_settings
        
        # Define public settings keys that don't require admin access
        setting_keys = [
            'general.applicationName',
            'general.timezone',
            'instructions.login',
            'instructions.reservation', 
            'instructions.email',
            'instructions.usernameFieldLabel',
            'instructions.passwordFieldLabel',
            'email.contactEmail'
        ]
        
        # Get settings from database
        settings_dict = get_multiple_settings(setting_keys)
        
        # Build response with public configuration
        config_data = {
            "app": {
                "name": settings_dict.get('general.applicationName', 'Containers on the Fly'),
                "timezone": settings_dict.get('general.timezone', 'UTC'),
                "contactEmail": settings_dict.get('email.contactEmail', '')
            },
            "instructions": {
                "login": settings_dict.get('instructions.login', ''),
                "reservation": settings_dict.get('instructions.reservation', ''),
                "email": settings_dict.get('instructions.email', ''),
                "usernameFieldLabel": settings_dict.get('instructions.usernameFieldLabel', 'Username'),
                "passwordFieldLabel": settings_dict.get('instructions.passwordFieldLabel', 'Password')
            },
            "login": {
                "loginText": "Login with your credentials.",
                "usernameField": "Username", 
                "passwordField": "Password"
            }
        }
        
        return api_response(True, "Public configuration retrieved successfully", config_data)
        
    except Exception as e:
        log.error(f"Error retrieving application settings: {str(e)}")
        return api_response(False, f"Error retrieving public configurations")