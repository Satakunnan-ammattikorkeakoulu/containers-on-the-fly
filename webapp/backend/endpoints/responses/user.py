from database import User, Session, UserWhitelist
from helpers.server import Response, ORMObjectToDict
from settings import settings
from helpers.auth import CreateLoginToken, HashPassword, IsCorrectPassword, CheckToken, GetLDAPUser, GetRole
from fastapi import HTTPException, status
from datetime import datetime
from logger import log
import hashlib
import base64

def login(username, password):
  '''
    Logins the user with the given username and password, if password logins are enabled.
      Parameters:
        username: Email address
        password: Password
      
      Returns:
        If login was succesfull, will return back the generated token that user can use further on.
        Otherwise tells that the username or password was invalid.
  '''
  if username == "" or username is None: raise HTTPException(status_code=400, detail="username cannot be empty.")
  if password == "" or password is None: raise HTTPException(status_code=400, detail="password cannot be empty.")

  with Session() as session:
    user = None
    loginType = settings.login["loginType"]
    useWhitelisting = settings.login["useWhitelist"]

    if loginType == "password":
      user = session.query(User).filter( User.email == username).first()
    elif loginType == "LDAP":
      ldapSuccess, response = GetLDAPUser(username, password)
      if ldapSuccess == False:
        return Response(False, response)
      user = session.query(User).filter( User.userId == response).first()

    whitelistEmail = session.query(UserWhitelist).filter( UserWhitelist.email == username ).first()
    if loginType == "password" and useWhitelisting and whitelistEmail == None:
      return Response(False, "You are not allowed to login (not whitelisted).")

    # User found
    if user:
      # Check that the password is correct (only for password logins)
      if (loginType == "password" and (user.password == "" or user.password is None)):
        raise HTTPException(status_code=400, detail="User password was not set yet. Please set the password first to login.")
      if loginType == "password" and IsCorrectPassword(base64.b64decode(user.passwordSalt), base64.b64decode(user.password), password) == False:
        raise HTTPException(status_code=400, detail="Incorrect password.")

      # Create login token and return it
      user.loginToken = CreateLoginToken()
      user.loginTokenCreatedAt = datetime.utcnow()
      session.commit()
      #log.info(f"User {user.email} logged in.")
      #log.info(user)
      return {
        "access_token": user.loginToken,
        "token_type": "bearer"
      }
    # User not found, invalid login credentials
    else:
      raise HTTPException(status_code=400, detail="User not found.")

def checkToken(token):
  ''' Checks that the given token is valid and has not expired.

      Parameters:
        token: token
      
      Returns:
        If token was ok, returns also back information about the user.
        Otherwise tells that the user is not currently logged in.
  '''
  tokenCheck = CheckToken(token)

  if (tokenCheck["status"] == True): return tokenCheck
  else:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid authentication credentials",
      headers={"WWW-Authenticate": "Bearer"},
    )

def createPassword(password):
  ''' For generating encrypted password for a user
      Parameters:
        password: password
  '''
  if password == "" or password is None:
    return Response(False, "Password cannot be empty.")
  hash = HashPassword(password)
  return Response(True, "Password created", {
    "password": str(hash["hashedPassword"]),
    "salt": str(hash['salt'])
  })

def profile(token):
  ''' For getting information about user with the given token.
      Parameters:
        token: User login token
  '''
  with Session() as session:
    user = session.query(User).filter( User.loginToken == token ).first()
  if user is None: return Response(False, "User not found.")
  else:
    userDetails = {}
    userDetails["userId"] = user.userId
    userDetails["email"] = user.email
    userDetails["createdAt"] = user.userCreatedAt
    userDetails["role"] = GetRole(user.email)
    return Response(True, "User details found", { "user": userDetails })