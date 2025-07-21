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
        Legacy method - all settings are now loaded directly from database when needed.
        This method is kept for compatibility but does nothing.
        '''
        pass

settings = Settings()