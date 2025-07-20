# Settings handler
# To make changes to settings, please use the file settings.json

import json
import os
import sys
import re

# Example taken from here: https://gist.github.com/nadya-p/b25519cf3a74d1bed86ed9b1d8c71692
# Handler for loading the settings.json file
# Initialized class can be used with:
#   from backend.settings import settings
#   settings.app["name"]

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

    def CheckRequiredSettings(self):
        '''
        Checks that the settings file is found and that all the required settings are found.
        Calls os.exit() if any problems were found.
        '''
        s = self

        # TODO: Could probably do a loop and then match all these against a dictionary array

        v = ""

        # app
        if not hasattr(s, 'app'): die("app")
        if "name" not in s.app: die("app.name")
        if "logoUrl" not in s.app: die("app.logoUrl")
        if "url" not in s.app: die("app.url")
        if "clientUrl" not in s.app: die("app.clientUrl")
        if "port" not in s.app: die("app.port")
        if "production" not in s.app: die("app.production")
        if "addTestDataInDevelopment" not in s.app: die("app.addTestDataInDevelopment")
        if "timezone" not in s.app: die("app.timezone")
        # reservation
        if not hasattr(s, 'reservation'): die("reservation")
        if "minimumDuration" not in s.reservation: die("reservation.minimumDuration")
        if "maximumDuration" not in s.reservation: die("reservation.maximumDuration")
        # login
        if not hasattr(s, 'login'): die("login")
        if "loginType" not in s.login: die("login.loginType")
        # session
        if not hasattr(s, 'session'): die("session")
        if "timeoutMinutes" not in s.session: die("session.timeoutMinutes")
        # database
        if not hasattr(s, 'database'): die("database")
        if "engineUri" not in s.database: die("database.engineUri")
        if "debugPrinting" not in s.database: die("database.debugPrinting")
        # docker
        if not hasattr(s, 'docker'): die("docker")
        if "enabled" not in s.docker: die("docker.enabled")
        if "mountUser" not in s.docker: die("docker.mountUser")
        if "mountGroup" not in s.docker: die("docker.mountGroup")
        if "shm_size" not in s.docker: die("docker.shm_size")
        if "port_range_start" not in s.docker: die("docker.port_range_start")
        if "port_range_end" not in s.docker: die("docker.port_range_end")
        if "sendEmail" not in s.docker: die("docker.sendEmail")
        # email
        if not hasattr(s, 'email'): die("email")
        if "helpEmailAddress" not in s.email: die("email.helpEmailAddress")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        json.dump(self.__dict__, open(self._config_location, 'w'))

settings = Settings()