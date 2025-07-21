# Settings handler
# To make changes to settings, please use the file settings.json

import json
import os
import sys
import re

# Import SystemSetting when needed, not at module level to avoid circular imports
# Circular imports can occur because helpers.tables modules may import settings

# Example taken from here: https://gist.github.com/nadya-p/b25519cf3a74d1bed86ed9b1d8c71692
# Handler for loading the settings.json file
# Initialized class can be used with:
#   from backend.settings import settings
#   settings.app["url"]

def die(text):
  import os
  print("Settings file is missing a required setting: ", text)
  os._exit(0)

class Settings:
    _config_location = 'settings.json'
    adminToken = ""

    def __init__(self):
      if os.path.exists(self._config_location):
        with open(self._config_location, 'r') as handle:
          fixed_json = ''.join(line for line in handle if not re.match(r'^\s*//.*', line))

        self.__dict__ = json.loads(fixed_json)
      else:
        sys.exit("COULD NOT LOAD THE SETTINGS.JSON FILE")
      # Check that the settings are valid
      self.CheckRequiredSettings()
      # Database settings will be loaded on-demand when needed
      self._database_settings_loaded = False

    def CheckRequiredSettings(self):
        '''
        Checks that the settings file is found and that all the required settings are found.
        Calls os.exit() if any problems were found.
        '''
        s = self

        # TODO: Could probably do a loop and then match all these against a dictionary array

        # app
        if not hasattr(s, 'app'): die("app")
        if "logoUrl" not in s.app: die("app.logoUrl")
        if "url" not in s.app: die("app.url")
        if "clientUrl" not in s.app: die("app.clientUrl")
        if "port" not in s.app: die("app.port")
        if "production" not in s.app: die("app.production")
        if "addTestDataInDevelopment" not in s.app: die("app.addTestDataInDevelopment")
        # login (now managed via database, create default if missing)
        if not hasattr(s, 'login'):
            s.login = {
                "loginType": "password",
                "ldap": {
                    "ldap_url": "",
                    "usernameFormat": "",
                    "passwordFormat": "",
                    "ldapDomain": "",
                    "searchMethod": "",
                    "accountField": "",
                    "emailField": ""
                }
            }
        if "loginType" not in s.login:
            s.login["loginType"] = "password"
        if "ldap" not in s.login:
            s.login["ldap"] = {
                "ldap_url": "",
                "usernameFormat": "",
                "passwordFormat": "",
                "ldapDomain": "",
                "searchMethod": "",
                "accountField": "",
                "emailField": ""
            }
        if s.login["loginType"] not in ["password", "LDAP", "hybrid"]: 
            print("Warning: login.loginType must be 'password', 'LDAP', or 'hybrid'. Defaulting to 'password'.")
            s.login["loginType"] = "password"
        # session (now managed via database, create default if missing)
        if not hasattr(s, 'session'):
            s.session = {"timeoutMinutes": 1440}
        if "timeoutMinutes" not in s.session:
            s.session["timeoutMinutes"] = 1440
        # database
        if not hasattr(s, 'database'): die("database")
        if "engineUri" not in s.database: die("database.engineUri")
        if "debugPrinting" not in s.database: die("database.debugPrinting")
        # docker
        if not hasattr(s, 'docker'): die("docker")
        if "enabled" not in s.docker: die("docker.enabled")
        # mountUser and mountGroup are hardcoded in docker_functionality.py, not used from settings
        if "shm_size" not in s.docker: die("docker.shm_size")
        if "port_range_start" not in s.docker: die("docker.port_range_start")
        if "port_range_end" not in s.docker: die("docker.port_range_end")
        if "sendEmail" not in s.docker: 
            s.docker["sendEmail"] = False  # Default to False if missing
        # email (now managed via database, create default if missing)
        if not hasattr(s, 'email'):
            s.email = {"helpEmailAddress": "admin@localhost"}
        if "helpEmailAddress" not in s.email:
            s.email["helpEmailAddress"] = "admin@localhost"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        json.dump(self.__dict__, open(self._config_location, 'w'))
        
    def ensure_database_settings_loaded(self):
        '''
        Ensures database settings are loaded, but only loads them once on-demand.
        '''
        if not self._database_settings_loaded:
            self.load_settings_from_database()
            self._database_settings_loaded = True
    
    def load_settings_from_database(self):
        '''
        Overrides settings from the database if they exist.
        This allows settings to be changed through the admin interface.
        '''
        try:
            # Import here to avoid circular imports
            # This may fail during database initialization/migration
            import sys
            if 'database' in sys.modules and hasattr(sys.modules['database'], 'SystemSetting'):
                from helpers.tables.SystemSetting import getSetting
            else:
                # Database not fully initialized yet, skip database settings
                return
            
            # Override login type from database if it exists
            login_type = getSetting('auth.loginType', None, 'text')
            if login_type is not None:
                self.login["loginType"] = login_type
                
            # Override session timeout from database if it exists
            session_timeout = getSetting('auth.sessionTimeoutMinutes', None, 'integer')
            if session_timeout is not None:
                self.session["timeoutMinutes"] = session_timeout
                
            # Override LDAP settings from database if they exist
            if self.login["loginType"] in ["LDAP", "hybrid"]:
                ldap_url = getSetting('auth.ldap.url', None, 'text')
                if ldap_url is not None and ldap_url != '':
                    self.login["ldap"]["ldap_url"] = ldap_url
                    
                username_format = getSetting('auth.ldap.usernameFormat', None, 'text')
                if username_format is not None and username_format != '':
                    self.login["ldap"]["usernameFormat"] = username_format
                    
                password_format = getSetting('auth.ldap.passwordFormat', None, 'text')
                if password_format is not None and password_format != '':
                    self.login["ldap"]["passwordFormat"] = password_format
                    
                ldap_domain = getSetting('auth.ldap.domain', None, 'text')
                if ldap_domain is not None and ldap_domain != '':
                    self.login["ldap"]["ldapDomain"] = ldap_domain
                    
                search_method = getSetting('auth.ldap.searchMethod', None, 'text')
                if search_method is not None and search_method != '':
                    self.login["ldap"]["searchMethod"] = search_method
                    
                account_field = getSetting('auth.ldap.accountField', None, 'text')
                if account_field is not None and account_field != '':
                    self.login["ldap"]["accountField"] = account_field
                    
                email_field = getSetting('auth.ldap.emailField', None, 'text')
                if email_field is not None and email_field != '':
                    self.login["ldap"]["emailField"] = email_field
        except Exception as e:
            # This is expected during database initialization/migration due to circular imports
            # Just continue with file-based settings
            if "circular import" not in str(e).lower():
                print(f"Warning: Could not load database settings: {str(e)}")
            pass

settings = Settings()