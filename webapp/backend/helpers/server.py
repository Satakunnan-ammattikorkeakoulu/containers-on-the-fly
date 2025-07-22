from typing import Union
from fastapi import HTTPException, status
from sqlalchemy import inspect
from sqlalchemy.ext.hybrid import hybrid_property
from helpers.auth import *
from database import User, Session
import requests
import json
from os import sys
from settings_handler import settings_handler

def Response(status, message, extraData = None):
  response = {
    "status": status,
    "message": message
  }
  if extraData is not None:
    response["data"] = extraData
  return response

def ForceAuthentication(token: str, roleRequired: str = None) -> Union[bool,HTTPException]:
  '''
  Checks if user is logged in by using the token passed.
  Parameters:
    token: Token
    roleRequired: If user is required to be in a specific role, that role should be passed here
  Returns:
    True if is user is logged in, otherwise will raise HTTPException.
  '''
  wrongRole = False
  if (IsLoggedIn(token)):
    if roleRequired is not None:
      with Session() as session:
        user = session.query(User).filter( User.loginToken == token ).first()
      if GetRole(user.email) == roleRequired:
        return True
      else:
        wrongRole = True
    else:
      return True
  
  detailMessage = "Invalid authentication credentials"
  if wrongRole == True:
    detailMessage = detailMessage + " - Wrong role"
  raise HTTPException(
    status_code = status.HTTP_401_UNAUTHORIZED,
    detail = detailMessage,
    headers = {"WWW-Authenticate": "Bearer"},
  )

def ORMObjectToDict(self):
    dict_ = {}
    for key in self.__mapper__.c.keys():
        # Going through all the keys one by one
        if not key.startswith('_'):
            # Cast all bytes to strings
            if isinstance(getattr(self, key), bytes):
              dict_[key] = str(getattr(self, key))
            # Otherwise do the casting automatically
            else:
              dict_[key] = getattr(self, key)

    for key, prop in inspect(self.__class__).all_orm_descriptors.items():
        if isinstance(prop, hybrid_property):
            dict_[key] = getattr(self, key)
    return dict_

def CheckIp(ip):
  allowed_ips = settings_handler.getSetting("admincli.allowedIpAddresses")
  if allowed_ips: # Check whether the list exists
    if len(allowed_ips) > 0 and ip not in allowed_ips:
      raise HTTPException(
        status_code = status.HTTP_403_FORBIDDEN,
        detail = "IP not found in allowed ip list in settings.json. Refusing access.",
        headers = {"WWW-Authenticate": "Bearer"})
    else: return True
  else: return True

def CallAdminAPI(method, endpoint, token = "", params = {}, data = {}, headers=True):
  if headers == True: headers = {"Authorization": "Bearer " + token}
  else: headers = {}
  admin_address = settings_handler.getSetting("admincli.address")
  if not admin_address: # Check whether the address exists in settings
    print("\nAdmin API Call Failed Exiting App...")
    print("No address specified in settings.json")
    sys.exit()
  if method == "get":
    response = requests.get("http://" + admin_address + "/api/" + endpoint,
                            params=params, headers=headers)
  elif method == "post":
    response = requests.post("http://" + admin_address + "/api/" + endpoint,
                            data=data, headers=headers)
  #print(response.text)
  if response.ok != True:
    if response.status_code == 500:
      print("Internal Server Error")
      sys.exit()
    print("\nAdmin API Call Failed Exiting App...")
    print(json.loads(response.text)["detail"])
    sys.exit()

  data = json.loads(response.text)
  return data