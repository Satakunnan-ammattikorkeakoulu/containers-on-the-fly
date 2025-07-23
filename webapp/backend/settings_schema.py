# Settings Schema Definition
# This file defines all settings used throughout the Containers on the Fly application
# It serves as the single source of truth for setting definitions, validation rules, and metadata

from typing import Dict, Any, Optional, List, Union
from enum import Enum

class SettingSource(Enum):
    FILE = "file"
    DATABASE = "database"

class SettingType(Enum):
    TEXT = "text"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    EMAIL = "email"
    JSON = "json"
    FLOAT = "float"

class SettingSetting:
    """Definition of a single setting with all its metadata"""
    
    def __init__(
        self, 
        source: SettingSource, 
        data_type: SettingType, 
        default: Any = None, 
        required: bool = False,
        description: str = "",
        validation: Optional[callable] = None,
        allowed_values: Optional[List[Any]] = None,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None
    ):
        self.source = source
        self.data_type = data_type
        self.default = default
        self.required = required
        self.description = description
        self.validation = validation
        self.allowed_values = allowed_values
        self.min_value = min_value
        self.max_value = max_value

# Complete Settings Schema
SETTINGS_SCHEMA: Dict[str, SettingSetting] = {
    
    # ===== FILE-BASED SETTINGS (Infrastructure Configuration) =====
    # These are loaded from settings.json and cannot be changed at runtime
    
    # App Configuration
    "app.url": SettingSetting(
        SettingSource.FILE, SettingType.TEXT, required=True,
        description="Base URL where the application is hosted"
    ),
    "app.serverIp": SettingSetting(
        SettingSource.FILE, SettingType.TEXT, required=True,
        description="Server IP address for internal communication"
    ),
    "app.clientUrl": SettingSetting(
        SettingSource.FILE, SettingType.TEXT, required=True,
        description="Frontend application URL"
    ),
    "app.logoUrl": SettingSetting(
        SettingSource.FILE, SettingType.TEXT, default="/static/logos/logo.png",
        description="Path to the application logo"
    ),
    "app.port": SettingSetting(
        SettingSource.FILE, SettingType.INTEGER, required=True,
        description="Port where the backend server runs"
    ),
    "app.production": SettingSetting(
        SettingSource.FILE, SettingType.BOOLEAN, default=True,
        description="Whether the application runs in production mode"
    ),
    "app.addTestDataInDevelopment": SettingSetting(
        SettingSource.FILE, SettingType.BOOLEAN, default=False,
        description="Add test data when running in development mode"
    ),
    
    # Database Configuration
    "database.engineUri": SettingSetting(
        SettingSource.FILE, SettingType.TEXT, required=True,
        description="Database connection string"
    ),
    "database.debugPrinting": SettingSetting(
        SettingSource.FILE, SettingType.BOOLEAN, default=False,
        description="Enable SQL query debug printing"
    ),
    
    # Docker Configuration
    "docker.registryAddress": SettingSetting(
        SettingSource.FILE, SettingType.TEXT, required=True,
        description="Docker registry address for container images"
    ),
    "docker.serverName": SettingSetting(
        SettingSource.FILE, SettingType.TEXT, required=True,
        description="Name identifier for this container server"
    ),
    "docker.port_range_start": SettingSetting(
        SettingSource.FILE, SettingType.INTEGER, default=20000,
        description="Start of port range for container services"
    ),
    "docker.port_range_end": SettingSetting(
        SettingSource.FILE, SettingType.INTEGER, default=20100,
        description="End of port range for container services"
    ),
    "docker.enabled": SettingSetting(
        SettingSource.FILE, SettingType.BOOLEAN, default=True,
        description="Enable Docker container functionality"
    ),
    "docker.shm_size": SettingSetting(
        SettingSource.FILE, SettingType.TEXT, default="1g",
        description="Shared memory size for containers"
    ),
    "docker.debugSkipGpuDedication": SettingSetting(
        SettingSource.FILE, SettingType.BOOLEAN, default=False,
        description="Skip actual GPU device dedication for testing (GPU reservation logic still runs)"
    ),
    
    # ===== DATABASE-BASED SETTINGS (User-Configurable) =====
    # These can be modified through the admin interface
    
    # General Application Settings
    "general.applicationName": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="Containers on the Fly",
        description="Application name displayed throughout the system"
    ),
    "general.timezone": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="UTC",
        description="System timezone for proper scheduling and logging"
    ),
    
    # Reservation Management Settings
    "reservation.minimumDuration": SettingSetting(
        SettingSource.DATABASE, SettingType.INTEGER, default=5,
        min_value=1, max_value=168,
        description="Minimum duration for container reservations in hours"
    ),
    "reservation.maximumDuration": SettingSetting(
        SettingSource.DATABASE, SettingType.INTEGER, default=72,
        min_value=1, max_value=720,
        description="Maximum duration for container reservations in hours"
    ),
    
    # UI Instructions and Labels
    "instructions.login": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="Information displayed on login page"
    ),
    "instructions.reservation": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="Instructions on reservation page"
    ),
    "instructions.email": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="Instructions included in emails"
    ),
    "instructions.usernameFieldLabel": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="Username",
        description="Username field label on login page"
    ),
    "instructions.passwordFieldLabel": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="Password",
        description="Password field label on login page"
    ),
    
    # Access Control Settings
    "access.blacklistEnabled": SettingSetting(
        SettingSource.DATABASE, SettingType.BOOLEAN, default=False,
        description="Enable email blacklist for access control"
    ),
    "access.whitelistEnabled": SettingSetting(
        SettingSource.DATABASE, SettingType.BOOLEAN, default=False,
        description="Enable email whitelist for access control"
    ),
    
    # Email Configuration Settings
    "email.sendEmail": SettingSetting(
        SettingSource.DATABASE, SettingType.BOOLEAN, default=False,
        description="Enable sending emails from the system"
    ),
    "email.smtpServer": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="SMTP server address"
    ),
    "email.smtpPort": SettingSetting(
        SettingSource.DATABASE, SettingType.INTEGER, default=587,
        min_value=1, max_value=65535,
        description="SMTP server port"
    ),
    "email.smtpUsername": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="SMTP username for authentication"
    ),
    "email.smtpPassword": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="SMTP password for authentication"
    ),
    "email.fromEmail": SettingSetting(
        SettingSource.DATABASE, SettingType.EMAIL, default="",
        description="From email address for outgoing messages"
    ),
    "email.contactEmail": SettingSetting(
        SettingSource.DATABASE, SettingType.EMAIL, default="",
        description="Admin contact email address"
    ),
    
    # Notification Settings
    "notifications.containerAlertsEnabled": SettingSetting(
        SettingSource.DATABASE, SettingType.BOOLEAN, default=False,
        description="Enable container failure alerts"
    ),
    "notifications.alertEmails": SettingSetting(
        SettingSource.DATABASE, SettingType.JSON, default=[],
        description="Email addresses for alerts (JSON array)"
    ),
    
    # Authentication Settings
    "auth.loginType": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="password",
        allowed_values=["password", "ldap", "hybrid"],
        description="Authentication method (password, LDAP, hybrid)"
    ),
    "auth.sessionTimeoutMinutes": SettingSetting(
        SettingSource.DATABASE, SettingType.INTEGER, default=1440,
        min_value=5, max_value=10080,
        description="Session timeout in minutes"
    ),
    
    # LDAP Authentication Settings
    "auth.ldap.url": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="LDAP server URL"
    ),
    "auth.ldap.usernameFormat": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="LDAP username format template"
    ),
    "auth.ldap.passwordFormat": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="LDAP password format template"
    ),
    "auth.ldap.domain": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="LDAP domain"
    ),
    "auth.ldap.searchMethod": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="LDAP search method"
    ),
    "auth.ldap.accountField": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="LDAP account field for user mapping"
    ),
    "auth.ldap.emailField": SettingSetting(
        SettingSource.DATABASE, SettingType.TEXT, default="",
        description="LDAP email field for user mapping"
    ),
}

# Helper functions for schema access
def get_setting_definition(key: str) -> Optional[SettingSetting]:
    """Get the setting definition for a given key"""
    return SETTINGS_SCHEMA.get(key)

def get_file_settings() -> Dict[str, SettingSetting]:
    """Get all settings that are stored in files"""
    return {k: v for k, v in SETTINGS_SCHEMA.items() if v.source == SettingSource.FILE}

def get_database_settings() -> Dict[str, SettingSetting]:
    """Get all settings that are stored in database"""
    return {k: v for k, v in SETTINGS_SCHEMA.items() if v.source == SettingSource.DATABASE}

def get_required_settings() -> Dict[str, SettingSetting]:
    """Get all settings that are required"""
    return {k: v for k, v in SETTINGS_SCHEMA.items() if v.required}

def get_settings_by_prefix(prefix: str) -> Dict[str, SettingSetting]:
    """Get all settings that start with a given prefix"""
    return {k: v for k, v in SETTINGS_SCHEMA.items() if k.startswith(prefix)}

def validate_setting_value(key: str, value: Any) -> tuple[bool, Optional[str]]:
    """
    Validate a setting value against its schema definition
    
    Returns:
        tuple: (is_valid, error_message)
    """
    setting_def = get_setting_definition(key)
    if not setting_def:
        return False, f"Unknown setting key: {key}"
    
    if value is None:
        if setting_def.required:
            return False, f"Required setting {key} cannot be None"
        return True, None
    
    # Type validation
    if setting_def.data_type == SettingType.INTEGER:
        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                return False, f"Setting {key} must be an integer"
        
        if setting_def.min_value is not None and value < setting_def.min_value:
            return False, f"Setting {key} must be at least {setting_def.min_value}"
        if setting_def.max_value is not None and value > setting_def.max_value:
            return False, f"Setting {key} must be at most {setting_def.max_value}"
    
    elif setting_def.data_type == SettingType.BOOLEAN:
        if not isinstance(value, bool):
            if isinstance(value, str):
                if value.lower() in ('true', '1', 'yes', 'on'):
                    value = True
                elif value.lower() in ('false', '0', 'no', 'off'):
                    value = False
                else:
                    return False, f"Setting {key} must be a boolean value"
            else:
                return False, f"Setting {key} must be a boolean value"
    
    elif setting_def.data_type == SettingType.EMAIL:
        if not isinstance(value, str):
            return False, f"Setting {key} must be a string"
        if value and '@' not in value:
            return False, f"Setting {key} must be a valid email address"
    
    elif setting_def.data_type == SettingType.TEXT:
        if not isinstance(value, str):
            return False, f"Setting {key} must be a string"
    
    # Allowed values validation
    if setting_def.allowed_values and value not in setting_def.allowed_values:
        return False, f"Setting {key} must be one of: {', '.join(map(str, setting_def.allowed_values))}"
    
    # Custom validation
    if setting_def.validation and not setting_def.validation(value):
        return False, f"Setting {key} failed custom validation"
    
    return True, None