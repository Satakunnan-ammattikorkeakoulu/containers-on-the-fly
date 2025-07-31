from database import User, Session, UserWhitelist, UserBlacklist
from settings_handler import getSetting
from helpers.server import Response
from helpers.auth import CreateLoginToken, HashPassword, IsCorrectPassword, CheckToken, GetLDAPUser, GetRole
from fastapi import HTTPException, status
from datetime import datetime, timezone
import base64

def login(username, password):
  '''
    Logins the user with the given username and password using the configured authentication method.
      Parameters:
        username: Email address
        password: Password
      
      Returns:
        If login was successful, will return back the generated token that user can use further on.
        Otherwise tells that the username or password was invalid.
  '''
  if username == "" or username is None: raise HTTPException(status_code=400, detail="username cannot be empty.")
  if password == "" or password is None: raise HTTPException(status_code=400, detail="password cannot be empty.")

  with Session() as session:
    # Get auth settings from database
    loginType = getSetting('auth.loginType')
    useWhitelisting = getSetting('access.whitelistEnabled')
    useBlacklisting = getSetting('access.blacklistEnabled')

    # Look up user by email first for any auth type
    user = session.query(User).filter(User.email == username).first()
    
    # Check blacklist first - this overrides whitelist and denies access immediately
    if useBlacklisting:
      blacklistEmail = session.query(UserBlacklist).filter(UserBlacklist.email == username).first()
      if blacklistEmail is not None:
        return Response(False, "You are not allowed to login (blacklisted).")

    # Check whitelist if enabled
    if useWhitelisting:
      whitelistEmail = session.query(UserWhitelist).filter(UserWhitelist.email == username).first()
      if whitelistEmail is None:
        return Response(False, "You are not allowed to login (not whitelisted).")

    # Helper function to create login token
    def create_successful_login(user):
      user.loginToken = CreateLoginToken()
      user.loginTokenCreatedAt = datetime.now(timezone.utc)
      session.commit()
      return {
        "access_token": user.loginToken,
        "token_type": "bearer"
      }
    
    # Try password authentication
    def try_password_auth():
      # Check if user exists and has password set
      if not user:
        raise HTTPException(status_code=400, detail="User not found.")
      
      if user.password == "" or user.password is None:
        raise HTTPException(status_code=400, detail="User password was not set yet. Please set the password first to login.")
      
      if IsCorrectPassword(base64.b64decode(user.passwordSalt), base64.b64decode(user.password), password) == False:
        raise HTTPException(status_code=400, detail="Incorrect password.")
      
      # Password is correct
      return create_successful_login(user)
    
    # Try LDAP authentication
    def try_ldap_auth():
      ldapSuccess, response = GetLDAPUser(username, password)
      if ldapSuccess == False:
        return Response(False, response)
      
      # Get or create user
      ldap_user = session.query(User).filter(User.userId == response).first()
      return create_successful_login(ldap_user)
    
    # Handle different login types
    if loginType == "password":
      return try_password_auth()
      
    # For backward compatibility, support the legacy LDAP-only option in case
    # it's still in the config file
    elif loginType == "LDAP":
      return try_ldap_auth()
      
    elif loginType == "hybrid":
      # Try password first if user exists and has password set
      if user and user.password and user.password != "":
        try:
          return try_password_auth()
        except HTTPException as e:
          # If password auth fails with incorrect password, try LDAP
          if e.status_code == 400 and e.detail == "Incorrect password.":
            return try_ldap_auth()
          # Re-raise other errors
          raise
      
      # No user or no password set, try LDAP
      return try_ldap_auth()
    
    else:
      # Unknown login type - fall back to password authentication as the safest option
      return try_password_auth()

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

def hasPassword(token):
  ''' Checks if the user has a password set.
      Parameters:
        token: User login token
  '''
  with Session() as session:
    user = session.query(User).filter(User.loginToken == token).first()
    if user is None:
      return Response(False, "User not found.")
    
    # Check if password is set (not None and not empty string)
    hasPassword = user.password is not None and user.password != ""
    return Response(True, "Password status checked", {"hasPassword": hasPassword})

def changePassword(token, currentPassword, newPassword):
  ''' Changes the user's password.
      Parameters:
        token: User login token
        currentPassword: Current password
        newPassword: New password
  '''
  if currentPassword == "" or currentPassword is None:
    return Response(False, "Current password cannot be empty.")
  if newPassword == "" or newPassword is None:
    return Response(False, "New password cannot be empty.")
  if len(newPassword) < 5:
    return Response(False, "New password must be at least 5 characters long.")
  
  with Session() as session:
    user = session.query(User).filter(User.loginToken == token).first()
    if user is None:
      return Response(False, "User not found.")
    
    # Check if user has a password set
    if user.password is None or user.password == "":
      return Response(False, "Password is not set for this account. Cannot change password.")
    
    # Verify current password
    if not IsCorrectPassword(base64.b64decode(user.passwordSalt), base64.b64decode(user.password), currentPassword):
      return Response(False, "Current password is incorrect.")
    
    # Hash and set new password
    hash = HashPassword(newPassword)
    user.password = base64.b64encode(hash["hashedPassword"]).decode('utf-8')
    user.passwordSalt = base64.b64encode(hash["salt"]).decode('utf-8')
    session.commit()
    
    return Response(True, "Password changed successfully.")