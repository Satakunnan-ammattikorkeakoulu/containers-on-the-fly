# SystemSetting table management functionality
from database import SystemSetting, Session
import json

def getSetting(setting_key: str, default_value=None, data_type: str = "text"):
    """
    Get a setting value by key, return default if not found.
    
    Args:
        setting_key: The key to look up
        default_value: Value to return if setting doesn't exist
        data_type: Data type for the setting (used when creating new)
    
    Returns:
        The setting value, properly parsed according to data type
    """
    with Session() as session:
        setting = session.query(SystemSetting).filter(
            SystemSetting.settingKey == setting_key
        ).first()
        
        if not setting:
            return default_value
            
        # Parse based on data type
        if setting.dataType == "boolean":
            return setting.settingValue.lower() == "true" if setting.settingValue else False
        elif setting.dataType == "integer":
            return int(setting.settingValue) if setting.settingValue else default_value
        elif setting.dataType == "json":
            return json.loads(setting.settingValue) if setting.settingValue else default_value
        else:  # text, email
            return setting.settingValue

def setSetting(setting_key: str, value, data_type: str = "text", description: str = None):
    """
    Set a setting value by key, create if doesn't exist.
    
    Args:
        setting_key: The key to set
        value: The value to set
        data_type: Data type for the setting
        description: Optional description
    
    Returns:
        Boolean indicating success
    """
    try:
        with Session() as session:
            setting = session.query(SystemSetting).filter(
                SystemSetting.settingKey == setting_key
            ).first()
            
            # Convert value to string for storage
            if data_type == "boolean":
                string_value = "true" if value else "false"
            elif data_type == "integer":
                string_value = str(value) if value is not None else None
            elif data_type == "json":
                string_value = json.dumps(value) if value is not None else None
            else:  # text, email
                string_value = str(value) if value is not None else None
            
            if setting:
                # Update existing
                setting.settingValue = string_value
                setting.dataType = data_type
                if description:
                    setting.description = description
            else:
                # Create new
                setting = SystemSetting(
                    settingKey=setting_key,
                    settingValue=string_value,
                    dataType=data_type,
                    description=description
                )
                session.add(setting)
            
            session.commit()
            return True
    except Exception as e:
        print(f"Error setting {setting_key}: {e}")
        return False

def getMultipleSettings(setting_keys: list):
    """
    Get multiple settings at once.
    
    Args:
        setting_keys: List of setting keys to retrieve
        
    Returns:
        Dictionary with key-value pairs
    """
    with Session() as session:
        settings = session.query(SystemSetting).filter(
            SystemSetting.settingKey.in_(setting_keys)
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
                
        return result 