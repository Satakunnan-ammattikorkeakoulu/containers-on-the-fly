from typing import Tuple
import os
import hashlib
import hmac
import random
import string
from database import User, Session, UserWhitelist
from settings_handler import getSetting
import helpers.server
#import ldap3 as ldap
import ldap
from datetime import timedelta
import datetime
import string
import secrets
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

def IsAdmin(userIdOrEmail) -> bool:
  '''
  Checks that the user with the given email address is in admin role.

  Parameters:
    userIdOrEmail: userId or email address of the user. Will use userId if integer is given, otherwise email address.
  Returns:
    True if is admin, False otherwise.
  '''
  with Session() as session:
    user = None
    if (isinstance(userIdOrEmail, int)):
      user = session.query(User).filter( User.userId == userIdOrEmail ).first()
    else:
      user = session.query(User).filter( User.email == userIdOrEmail ).first()

    if (user == None): return False
    isAdmin = False
    for role in user.roles:
      if role.name == "admin": isAdmin = True
    return isAdmin

def GetRole(email : str) -> string:
  '''
  Gets the role (first found role from the database) for the user with the given email.
  Returns:
    'user' if role was not found for the user, otherwise the name of the role.
  '''
  with Session() as session:
    user = session.query(User).options(joinedload(User.roles)).filter( User.email == email ).first()
    session.close()

  if (user == None): return "user"

  userRole = "user"
  if (len(user.roles) > 0):
    userRole = user.roles[0].name
  return userRole

def IsLoggedIn(token : str):
  '''
  Checks if the passed token can be found from the database and has not expired.
  Parameters:
    token: token
  Returns:
    True if user is logged in, false otherwise.
  '''
  tokenResponse = CheckToken(token)
  if (tokenResponse["status"] == True): return True
  else: return False

def GetUserReservationLimits(userId: int) -> dict:
  '''
  Gets the user's reservation limits based on their roles.
  Applies the most permissive limits when user has multiple roles.
  
  Parameters:
    userId: The user's ID
  
  Returns:
    Dict with minDuration, maxDuration, and maxActiveReservations
  '''
  from database import UserRole, Role
  from helpers.tables.Role import getRoleReservationLimits
  
  with Session() as session:
    # Get all user roles explicitly assigned
    user_roles = session.query(Role).join(UserRole).filter(UserRole.userId == userId).all()
    
    # Add the 'everyone' role since it applies to all users
    everyone_role = session.query(Role).filter(Role.name == "everyone").first()
    if everyone_role and everyone_role not in user_roles:
      user_roles.append(everyone_role)
    
    # Check if user is admin
    isAdmin = any(role.name == "admin" for role in user_roles)
    
    # Default values based on whether user is admin
    default_min = 1  # 1 hour for all users
    default_max = 1440 if isAdmin else 48  # 60 days for admin, 48 hours for others
    default_active = 99 if isAdmin else 1
    
    # Start with the most restrictive defaults
    min_duration = float('inf')
    max_duration = 0
    max_active_reservations = 0
    
    # Apply the most permissive limits from all roles
    for role in user_roles:
      limits = getRoleReservationLimits(role.roleId)
      
      # Use the lowest minimum duration (most permissive)
      if limits['minDuration'] < min_duration:
        min_duration = limits['minDuration']
      
      # Use the highest maximum duration (most permissive)
      if limits['maxDuration'] > max_duration:
        max_duration = limits['maxDuration']
      
      # Use the highest max active reservations (most permissive)
      if limits['maxActiveReservations'] > max_active_reservations:
        max_active_reservations = limits['maxActiveReservations']
    
    # If no roles found, use defaults
    if min_duration == float('inf'):
      min_duration = default_min
    if max_duration == 0:
      max_duration = default_max
    if max_active_reservations == 0:
      max_active_reservations = default_active
    
    return {
      'minDuration': min_duration,
      'maxDuration': max_duration,
      'maxActiveReservations': max_active_reservations
    }

def CheckToken(token : str) -> object:
  '''
  Checks that the given token is valid and has not expired.
  Parameters:
    token: token
  Returns:
    Returns back a Response.
  Example return:
    { success: True, message: "Token OK.", data: { email: "test" } }
  '''
  if token == "" or token is None: return helpers.server.Response(False, "Token cannot be empty.")

  def timeNow(): return datetime.datetime.now(datetime.timezone.utc)
  from settings_handler import getSetting
  session_timeout = getSetting('auth.sessionTimeoutMinutes')
  minStartDate = timeNow() - timedelta(minutes=session_timeout)

  with Session() as session:
    user = session.query(User).filter( User.loginToken == token, User.loginTokenCreatedAt > minStartDate ).first()
    session.close()

  if user is not None:
    userRole = GetRole(user.email)
    # Get all user roles
    userRoles = []
    with Session() as session:
      from database import UserRole, Role
      user_roles = session.query(Role).join(UserRole).filter(UserRole.userId == user.userId).all()
      for role in user_roles:
        if role.name.lower() != 'everyone':  # Exclude 'everyone' role
          userRoles.append(role.name)
    
    # Get user's reservation limits
    reservationLimits = GetUserReservationLimits(user.userId)
    
    return helpers.server.Response(True, "Token OK.", { 
      "userId": user.userId, 
      "email": user.email, 
      "role": userRole, 
      "roles": userRoles,
      "reservationLimits": reservationLimits
    })
  else:
    return helpers.server.Response(False, "Invalid token.")

def get_authenticated_user_id(token: str) -> int:
  '''
  Authenticates the provided token and returns the user ID.
  This combines token validation and user ID extraction in one call.
  
  Parameters:
    token: The authentication token
  
  Returns:
    The authenticated user's ID
    
  Raises:
    HTTPException: If the token is invalid or expired
  '''
  auth_result = CheckToken(token)
  if not auth_result["status"]:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail=auth_result["message"],
      headers={"WWW-Authenticate": "Bearer"},
    )
  return auth_result["data"]["userId"]

def CreateLoginToken() -> str:
  '''
  Creates login token of 100 characters (including some special characters)
  and returns it back.
    Returns:
      the generated loginToken
  '''
  allowedChars = string.ascii_lowercase + string.ascii_uppercase + string.digits + "!_-"
  limit = 100
  return ''.join(random.choice(allowedChars) for _ in range(limit))

def HashPassword(password: str) -> Tuple[bytes, bytes]:
  """
  Hash the provided password with a randomly-generated salt and return the
  salt and hash to store in the database.
  
  Example usage:
    hash = HashPassword('correct horse battery staple')
  """
  salt = os.urandom(16)
  pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
  return { "salt": salt, "hashedPassword": pw_hash }

def IsCorrectPassword(salt: bytes, pw_hash: bytes, password: str) -> bool:
  """
  Given a previously-stored salt and hash, and a password provided by a user
  trying to log in, check whether the password is correct.

  Example usage:
    if IsCorrectPassword(hash['salt'], hash['hashedPassword'], 'correct horse battery staple') == True
  """
  return hmac.compare_digest(
    pw_hash,
    hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
  )

def create_password(length = 40):
  '''
  Creates a random password of the given length.
  Returns:
    (string) the generated password
  '''
  possible_chars = string.ascii_letters + string.digits
  random_password = "".join(secrets.choice(possible_chars) for _ in range(length))
  return random_password

def GetLDAPUser(username, password):
  from settings_handler import getSetting
  
  # Get LDAP settings from database
  ldap_url = getSetting('auth.ldap.url')
  username_format = getSetting('auth.ldap.usernameFormat')
  password_format = getSetting('auth.ldap.passwordFormat') 
  ldap_domain = getSetting('auth.ldap.domain')
  search_method = getSetting('auth.ldap.searchMethod')
  account_field = getSetting('auth.ldap.accountField')
  email_field = getSetting('auth.ldap.emailField')
  
  # Check if LDAP is properly configured
  if not all([ldap_url, username_format, password_format, ldap_domain, search_method, account_field, email_field]):
    return False, "LDAP is not properly configured"
    
  useWhitelisting = getSetting('access.whitelistEnabled')
  # Disable certificate checks
  ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
  l = ldap.initialize(ldap_url)
  l.set_option(ldap.OPT_NETWORK_TIMEOUT, 6)
  l.set_option(ldap.OPT_TIMEOUT, 6)
  l.set_option(ldap.OPT_REFERRALS, ldap.OPT_OFF)
  #print(os.getcwd())
  #l.set_option(ldap.OPT_X_TLS_CACERTFILE, os.getcwd()+"/certificate.pem")

  with Session() as session:
    try:
      l.simple_bind_s(username_format.replace("{username}", username), password_format.replace("{password}", password))
      result = l.search_s(ldap_domain, ldap.SCOPE_SUBTREE, search_method.replace("{username}", username), [account_field, email_field])
      account = result[0][1][account_field][0].decode("utf-8")
      if account != username:
        return False, "Wrong username / ldap username association"
      
      email = result[0][1][email_field][0].decode("utf-8")

      whitelistEmail = session.query(UserWhitelist).filter( UserWhitelist.email == email ).first()
      if useWhitelisting and whitelistEmail == None:
        return False, "You are not allowed to login (not whitelisted, LDAP)."

      user = session.query(User).filter( User.email == email ).first()
      # User not found? Create it and return the newly created user
      if user == None:
        newUser = User(
          email = email
        )
        session.add(newUser)
        session.commit()
        return True, session.query(User).filter( User.email == email ).first().userId
      # User found? Return it
      else:
        return True, user.userId
    except ldap.INVALID_CREDENTIALS:
      return False, "Wrong username or password."
    except ldap.SERVER_DOWN:
      return False, "Failed to connect to LDAP authentication service: Timeout."
    except Exception:
      return False, "Unknown error with the LDAP login!"