from database import User, Session, UserWhitelist, UserBlacklist
from settings_handler import get_setting
from helpers.server import api_response
from helpers.auth import create_login_token, hash_password, is_correct_password, check_token, get_ldap_user, get_role
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
    login_type = get_setting('auth.loginType')
    use_whitelisting = get_setting('access.whitelistEnabled')
    use_blacklisting = get_setting('access.blacklistEnabled')

    # Look up user by email first for any auth type
    user = session.query(User).filter(User.email == username).first()
    
    # Check blacklist first - this overrides whitelist and denies access immediately
    if use_blacklisting:
      blacklist_email = session.query(UserBlacklist).filter(UserBlacklist.email == username).first()
      if blacklist_email is not None:
        return api_response(False, "You are not allowed to login (blacklisted).")

    # Check whitelist if enabled
    if use_whitelisting:
      whitelist_email = session.query(UserWhitelist).filter(UserWhitelist.email == username).first()
      if whitelist_email is None:
        return api_response(False, "You are not allowed to login (not whitelisted).")

    # Helper function to create login token
    def create_successful_login(user):
      user.loginToken = create_login_token()
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
      
      if is_correct_password(base64.b64decode(user.passwordSalt), base64.b64decode(user.password), password) == False:
        raise HTTPException(status_code=400, detail="Incorrect password.")
      
      # Password is correct
      return create_successful_login(user)
    
    # Try LDAP authentication
    def try_ldap_auth():
      ldap_success, response = get_ldap_user(username, password)
      if ldap_success == False:
        return api_response(False, response)
      
      # Get or create user
      ldap_user = session.query(User).filter(User.userId == response).first()
      return create_successful_login(ldap_user)
    
    # Handle different login types
    if login_type == "password":
      return try_password_auth()

    # For backward compatibility, support the legacy LDAP-only option in case
    # it's still in the config file
    elif login_type == "LDAP":
      return try_ldap_auth()

    elif login_type == "hybrid":
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

def check_user_token(token):
  ''' Checks that the given token is valid and has not expired.

      Parameters:
        token: token
      
      Returns:
        If token was ok, returns also back information about the user.
        Otherwise tells that the user is not currently logged in.
  '''
  token_check = check_token(token)

  if (token_check["status"] == True): return token_check
  else:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid authentication credentials",
      headers={"WWW-Authenticate": "Bearer"},
    )

def create_password(password):
  ''' For generating encrypted password for a user
      Parameters:
        password: password
  '''
  if password == "" or password is None:
    return api_response(False, "Password cannot be empty.")
  hash = hash_password(password)
  return api_response(True, "Password created", {
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
  if user is None: return api_response(False, "User not found.")
  else:
    user_details = {}
    user_details["userId"] = user.userId
    user_details["email"] = user.email
    user_details["createdAt"] = user.userCreatedAt
    user_details["role"] = get_role(user.email)
    return api_response(True, "User details found", { "user": user_details })

def has_password(token):
  ''' Checks if the user has a password set.
      Parameters:
        token: User login token
  '''
  with Session() as session:
    user = session.query(User).filter(User.loginToken == token).first()
    if user is None:
      return api_response(False, "User not found.")

    # Check if password is set (not None and not empty string)
    has_password_set = user.password is not None and user.password != ""
    return api_response(True, "Password status checked", {"hasPassword": has_password_set})

def change_password(token, current_password, new_password):
  ''' Changes the user's password.
      Parameters:
        token: User login token
        current_password: Current password
        new_password: New password
  '''
  if current_password == "" or current_password is None:
    return api_response(False, "Current password cannot be empty.")
  if new_password == "" or new_password is None:
    return api_response(False, "New password cannot be empty.")
  if len(new_password) < 5:
    return api_response(False, "New password must be at least 5 characters long.")

  with Session() as session:
    user = session.query(User).filter(User.loginToken == token).first()
    if user is None:
      return api_response(False, "User not found.")

    # Check if user has a password set
    if user.password is None or user.password == "":
      return api_response(False, "Password is not set for this account. Cannot change password.")

    # Verify current password
    if not is_correct_password(base64.b64decode(user.passwordSalt), base64.b64decode(user.password), current_password):
      return api_response(False, "Current password is incorrect.")

    # Hash and set new password
    hash = hash_password(new_password)
    user.password = base64.b64encode(hash["hashedPassword"]).decode('utf-8')
    user.passwordSalt = base64.b64encode(hash["salt"]).decode('utf-8')
    session.commit()

    return api_response(True, "Password changed successfully.")