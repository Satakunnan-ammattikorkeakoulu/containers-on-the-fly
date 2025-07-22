# Settings Handler
# This module provides a unified interface for accessing all application settings
# from both settings.json files and the database SystemSetting table

import json
import os
import sys
import re
from typing import Any, Optional, Dict, List, Union
from settings_schema import SETTINGS_SCHEMA, SettingSource, SettingType, get_setting_definition, validate_setting_value

class UnifiedSettingsError(Exception):
    """Custom exception for settings-related errors"""
    pass

class UnifiedSettings:
    """
    Unified settings handler that provides a single interface for accessing
    all application settings from both file and database sources.
    """
    
    def __init__(self, config_location: str = 'settings.json'):
        self._config_location = config_location
        self._file_settings = {}
        self._database_settings_cache = {}
        self._cache_loaded = False
        
        # Load file-based settings immediately
        self._load_file_settings()
        
    def _load_file_settings(self):
        """Load settings from the settings.json file"""
        if not os.path.exists(self._config_location):
            raise UnifiedSettingsError(f"Settings file not found: {self._config_location}")
            
        try:
            with open(self._config_location, 'r') as handle:
                # Remove comment lines (starting with //)
                fixed_json = ''.join(line for line in handle if not re.match(r'^\s*//.*', line))
                self._file_settings = json.loads(fixed_json)
        except json.JSONDecodeError as e:
            raise UnifiedSettingsError(f"Invalid JSON in settings file: {e}")
        except Exception as e:
            raise UnifiedSettingsError(f"Error reading settings file: {e}")
        
        # Validate required file settings
        self._validate_required_file_settings()
    
    def _validate_required_file_settings(self):
        """Validate that all required file-based settings are present"""
        for key, setting_def in SETTINGS_SCHEMA.items():
            if setting_def.source == SettingSource.FILE and setting_def.required:
                if not self._get_nested_value(self._file_settings, key):
                    raise UnifiedSettingsError(f"Required setting missing: {key}")
    
    def _get_nested_value(self, data: dict, key: str) -> Any:
        """Get a nested value from a dictionary using dot notation (e.g., 'app.url')"""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if not isinstance(current, dict) or k not in current:
                return None
            current = current[k]
        
        return current
    
    def _set_nested_value(self, data: dict, key: str, value: Any):
        """Set a nested value in a dictionary using dot notation"""
        keys = key.split('.')
        current = data
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _load_database_settings_cache(self):
        """Load all database settings into cache for performance"""
        if self._cache_loaded:
            return
            
        try:
            # Import here to avoid circular imports
            from database import SystemSetting, Session
            import json
            
            # Get all database setting keys
            db_setting_keys = [key for key, setting_def in SETTINGS_SCHEMA.items() 
                             if setting_def.source == SettingSource.DATABASE]
            
            # Load all database settings at once
            with Session() as session:
                settings = session.query(SystemSetting).filter(
                    SystemSetting.settingKey.in_(db_setting_keys)
                ).all()
                
                result = {}
                for setting in settings:
                    # Parse based on data type
                    if setting.dataType == "boolean":
                        result[setting.settingKey] = setting.settingValue.lower() == "true" if setting.settingValue else False
                    elif setting.dataType == "integer":
                        result[setting.settingKey] = int(setting.settingValue) if setting.settingValue else None
                    elif setting.dataType == "json":
                        result[setting.settingKey] = json.loads(setting.settingValue) if setting.settingValue else None
                    else:  # text, email
                        result[setting.settingKey] = setting.settingValue
                        
                self._database_settings_cache = result
                self._cache_loaded = True
            
        except Exception as e:
            # Log error but don't fail - allow fallback to individual queries
            print(f"Warning: Could not load database settings cache: {e}")
    
    def _get_from_database(self, key: str, default: Any) -> Any:
        """Get a setting value from the database with caching"""
        # Try cache first
        if self._cache_loaded and key in self._database_settings_cache:
            return self._database_settings_cache[key]
        
        # Fallback to individual query
        try:
            from database import SystemSetting, Session
            import json
            
            with Session() as session:
                setting = session.query(SystemSetting).filter(
                    SystemSetting.settingKey == key
                ).first()
                
                if not setting:
                    return default
                    
                # Parse based on data type
                if setting.dataType == "boolean":
                    value = setting.settingValue.lower() == "true" if setting.settingValue else False
                elif setting.dataType == "integer":
                    value = int(setting.settingValue) if setting.settingValue else default
                elif setting.dataType == "json":
                    value = json.loads(setting.settingValue) if setting.settingValue else default
                else:  # text, email
                    value = setting.settingValue
            
            # Update cache
            if self._cache_loaded:
                self._database_settings_cache[key] = value
                
            return value
        except Exception as e:
            print(f"Warning: Error getting database setting {key}: {e}")
            return default
    
    def getSetting(self, key: str) -> Any:
        """
        Get a setting value by key from the appropriate source (file or database).
        
        Args:
            key: The setting key (e.g., 'app.url', 'general.applicationName')
            
        Returns:
            The setting value, properly typed according to schema
            
        Raises:
            UnifiedSettingsError: If the setting key is unknown
        """
        setting_def = get_setting_definition(key)
        if not setting_def:
            raise UnifiedSettingsError(f"Unknown setting key: {key}")
        
        # Use schema default only
        effective_default = setting_def.default
        
        if setting_def.source == SettingSource.FILE:
            # Get from file settings
            value = self._get_nested_value(self._file_settings, key)
            return value if value is not None else effective_default
        
        else:  # DATABASE
            # Load cache if not already loaded
            self._load_database_settings_cache()
            
            # Get from database
            return self._get_from_database(key, effective_default)
    
    def setSetting(self, key: str, value: Any) -> bool:
        """
        Set a setting value.
        
        Args:
            key: The setting key
            value: The value to set
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            UnifiedSettingsError: If the setting is file-based or validation fails
        """
        setting_def = get_setting_definition(key)
        if not setting_def:
            raise UnifiedSettingsError(f"Unknown setting key: {key}")
        
        if setting_def.source == SettingSource.FILE:
            raise UnifiedSettingsError(f"Cannot modify file-based setting: {key}")
        
        # Validate the value
        is_valid, error_msg = validate_setting_value(key, value)
        if not is_valid:
            raise UnifiedSettingsError(error_msg)
        
        try:
            from database import SystemSetting, Session
            import json
            
            with Session() as session:
                setting = session.query(SystemSetting).filter(
                    SystemSetting.settingKey == key
                ).first()
                
                # Convert value to string for storage
                if setting_def.data_type == SettingType.BOOLEAN:
                    string_value = "true" if value else "false"
                elif setting_def.data_type == SettingType.INTEGER:
                    string_value = str(value) if value is not None else None
                elif setting_def.data_type == SettingType.JSON:
                    string_value = json.dumps(value) if value is not None else None
                else:  # text, email
                    string_value = str(value) if value is not None else None
                
                if setting:
                    # Update existing
                    setting.settingValue = string_value
                    setting.dataType = setting_def.data_type.value
                else:
                    # Create new
                    setting = SystemSetting(
                        settingKey=key,
                        settingValue=string_value,
                        dataType=setting_def.data_type.value,
                        description=""
                    )
                    session.add(setting)
                
                session.commit()
                success = True
            
            # Update cache if successful
            if success and self._cache_loaded:
                # Parse the value according to data type for cache consistency
                if setting_def.data_type == SettingType.BOOLEAN:
                    cached_value = bool(value)
                elif setting_def.data_type == SettingType.INTEGER:
                    cached_value = int(value) if value is not None else None
                elif setting_def.data_type == SettingType.JSON:
                    cached_value = value  # Already parsed by setSetting
                else:
                    cached_value = str(value) if value is not None else None
                
                self._database_settings_cache[key] = cached_value
            
            return success
            
        except Exception as e:
            print(f"Error setting {key}: {e}")
            return False
    
    def getMultipleSettings(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple settings at once for better performance.
        
        Args:
            keys: List of setting keys to retrieve
            
        Returns:
            Dictionary with key-value pairs
        """
        result = {}
        file_keys = []
        db_keys = []
        
        # Separate keys by source
        for key in keys:
            setting_def = get_setting_definition(key)
            if not setting_def:
                raise UnifiedSettingsError(f"Unknown setting key: {key}")
            
            if setting_def.source == SettingSource.FILE:
                file_keys.append(key)
            else:
                db_keys.append(key)
        
        # Get file-based settings
        for key in file_keys:
            result[key] = self.getSetting(key)
        
        # Get database settings (batch load if not cached)
        if db_keys:
            if not self._cache_loaded:
                self._load_database_settings_cache()
            
            for key in db_keys:
                result[key] = self.getSetting(key)
        
        return result
    
    def getAllSettings(self) -> Dict[str, Any]:
        """Get all settings from both sources"""
        all_keys = list(SETTINGS_SCHEMA.keys())
        return self.getMultipleSettings(all_keys)
    
    def getSettingsByPrefix(self, prefix: str) -> Dict[str, Any]:
        """Get all settings that start with a given prefix"""
        matching_keys = [key for key in SETTINGS_SCHEMA.keys() if key.startswith(prefix)]
        return self.getMultipleSettings(matching_keys)
    
    def validateSetting(self, key: str, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a setting value without setting it.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        return validate_setting_value(key, value)
    
    def getSettingInfo(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata information about a setting.
        
        Returns:
            Dictionary with setting metadata or None if key doesn't exist
        """
        setting_def = get_setting_definition(key)
        if not setting_def:
            return None
        
        return {
            'key': key,
            'source': setting_def.source.value,
            'data_type': setting_def.data_type.value,
            'default': setting_def.default,
            'required': setting_def.required,
            'description': setting_def.description,
            'allowed_values': setting_def.allowed_values,
            'min_value': setting_def.min_value,
            'max_value': setting_def.max_value
        }
    
    def clearDatabaseCache(self):
        """Clear the database settings cache to force reload"""
        self._database_settings_cache.clear()
        self._cache_loaded = False
    
    def reloadFileSettings(self):
        """Reload settings from the file (useful for configuration changes)"""
        self._load_file_settings()
    
    # Legacy compatibility methods
    def CheckRequiredSettings(self):
        """Legacy compatibility method for checking required settings"""
        try:
            self._validate_required_file_settings()
            return True
        except UnifiedSettingsError:
            return False
    
    # Property access for backward compatibility with existing code
    @property 
    def app(self) -> Dict[str, Any]:
        """Get all app settings as a dictionary"""
        return {
            key.replace('app.', ''): self.getSetting(key) 
            for key in SETTINGS_SCHEMA.keys() 
            if key.startswith('app.')
        }
    
    @property
    def database(self) -> Dict[str, Any]:
        """Get all database connection settings as a dictionary"""
        return {
            key.replace('database.', ''): self.getSetting(key)
            for key in SETTINGS_SCHEMA.keys()
            if key.startswith('database.')
        }
    
    @property
    def docker(self) -> Dict[str, Any]:
        """Get all docker settings as a dictionary"""
        return {
            key.replace('docker.', ''): self.getSetting(key)
            for key in SETTINGS_SCHEMA.keys()
            if key.startswith('docker.')
        }

# Create global instance for backward compatibility
# This allows existing code to use: from settings_handler import settings_handler
settings_handler = UnifiedSettings()

# Convenience functions for direct access
def getSetting(key: str) -> Any:
    """Global convenience function to get a setting"""
    return settings_handler.getSetting(key)

def setSetting(key: str, value: Any) -> bool:
    """Global convenience function to set a setting"""
    return settings_handler.setSetting(key, value)

def getMultipleSettings(keys: List[str]) -> Dict[str, Any]:
    """Global convenience function to get multiple settings"""
    return settings_handler.getMultipleSettings(keys)