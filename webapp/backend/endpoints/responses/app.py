from helpers.server import Response
from settings import settings

def getPublicConfig() -> object:
    '''
    Returns public app configuration that doesn't require authentication.
    This includes app info, reservation limits, instruction messages, etc.
    
    Returns:
        object: Response object with public configuration data.
    '''
    try:
        from helpers.tables.SystemSetting import getMultipleSettings
        
        # Define public settings keys that don't require admin access
        setting_keys = [
            'instructions.login',
            'instructions.reservation', 
            'instructions.email',
            'email.contactEmail'
        ]
        
        # Get settings from database
        settings_dict = getMultipleSettings(setting_keys)
        
        # Build response with public configuration
        config_data = {
            "app": {
                "name": settings.app["name"],
                "timezone": settings.app["timezone"],
                "contactEmail": settings_dict.get('email.contactEmail', '')
            },
            "reservation": {
                "minimumDuration": settings.reservation["minimumDuration"],
                "maximumDuration": settings.reservation["maximumDuration"]
            },
            "instructions": {
                "login": settings_dict.get('instructions.login', ''),
                "reservation": settings_dict.get('instructions.reservation', ''),
                "email": settings_dict.get('instructions.email', '')
            },
            "login": {
                "loginText": "Login with your credentials.",
                "usernameField": "Username", 
                "passwordField": "Password"
            }
        }
        
        return Response(True, "Public configuration retrieved successfully", config_data)
        
    except Exception as e:
        print(f"Error retrieving application settings: {str(e)}")
        return Response(False, f"Error retrieving public configurations")