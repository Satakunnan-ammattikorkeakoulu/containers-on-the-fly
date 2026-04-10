"""Authentication and authorization utilities.

Provides functions for user authentication (local and LDAP), token management,
password hashing, role-based access control, and reservation limit calculation.
"""

from typing import Tuple
import os
import hashlib
import hmac
import random
import string
from database import User, Session, UserWhitelist
from helpers.settings_handler import get_setting
import helpers.server
#import ldap3 as ldap
import ldap
from datetime import timedelta
import datetime
import secrets
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

def is_admin(userIdOrEmail) -> bool:
  """Check whether a user has the admin role.

  Args:
      userIdOrEmail: User ID (int) or email address (str). Uses userId
          for lookup when an integer is provided, otherwise uses email.

  Returns:
      True if the user has the admin role, False otherwise.
  """
  with Session() as session:
    user = None
    if (isinstance(userIdOrEmail, int)):
      user = session.execute(select(User).where(User.userId == userIdOrEmail)).scalar_one_or_none()
    else:
      user = session.execute(select(User).where(User.email == userIdOrEmail)).scalar_one_or_none()

    if (user == None): return False
    result = False
    for role in user.roles:
      if role.name == "admin": result = True
    return result

def get_role(email : str) -> string:
  """Get the primary role for a user by email address.

  Looks up the user in the database and returns their first assigned role.

  Args:
      email: The user's email address.

  Returns:
      The name of the user's first role, or 'user' if no roles are assigned
      or the user is not found.
  """
  with Session() as session:
    user = session.execute(
      select(User).options(joinedload(User.roles)).where(User.email == email)
    ).unique().scalar_one_or_none()

    if (user == None): return "user"

    user_role = "user"
    if (len(user.roles) > 0):
      user_role = user.roles[0].name
    return user_role

def is_logged_in(token : str):
  """Check whether an authentication token is valid and not expired.

  Args:
      token: The authentication token to validate.

  Returns:
      True if the token is valid and the user is logged in, False otherwise.
  """
  token_response = check_token(token)
  if (token_response["status"] == True): return True
  else: return False

def get_user_reservation_limits(userId: int) -> dict:
  """Get the effective reservation limits for a user based on all their roles.

  When a user has multiple roles, the most permissive value is used for each
  limit (lowest minDuration, highest maxDuration, highest maxActiveReservations).
  The 'everyone' role is always included. Falls back to defaults if no roles
  define limits.

  Args:
      userId: The user's database ID.

  Returns:
      A dict with keys 'minDuration' (hours), 'maxDuration' (hours),
      and 'maxActiveReservations' (int).
  """
  from database import UserRole, Role, RoleReservationLimit

  with Session() as session:
    # Get all user roles explicitly assigned
    user_roles = session.execute(select(Role).join(UserRole).where(UserRole.userId == userId)).scalars().all()

    # Add the 'everyone' role since it applies to all users
    everyone_role = session.execute(select(Role).where(Role.name == "everyone")).scalar_one_or_none()
    if everyone_role and everyone_role not in user_roles:
      user_roles.append(everyone_role)

    # Check if user is admin
    user_is_admin = any(role.name == "admin" for role in user_roles)

    # Default values based on whether user is admin
    default_min = 1  # 1 hour for all users
    default_max = 1440 if user_is_admin else 48  # 60 days for admin, 48 hours for others
    default_active = 99 if user_is_admin else 1

    # Fetch all reservation limits for user's roles in a single query
    role_ids = [role.roleId for role in user_roles]
    role_limits_map = {}
    if role_ids:
      all_limits = session.execute(
        select(RoleReservationLimit).where(RoleReservationLimit.roleId.in_(role_ids))
      ).scalars().all()
      for limit in all_limits:
        role_limits_map[limit.roleId] = limit

    # Start with the most restrictive defaults
    min_duration = float('inf')
    max_duration = 0
    max_active_reservations = 0
    # Collect each role's explicit low-priority opinion (True/False). Missing
    # rows contribute nothing so an admin's explicit `False` on one role can
    # actually take effect — otherwise a user with a disabled role plus the
    # built-in "everyone" role (which may have no row) would still get LP via
    # the "no row = allow" fallback, making the admin's toggle meaningless.
    lp_opinions = []

    # Apply the most permissive limits from all roles
    for role in user_roles:
      # Determine per-role defaults
      if role.name == "admin":
        role_default_min, role_default_max, role_default_active = 1, 1440, 99
      else:
        role_default_min, role_default_max, role_default_active = 1, 48, 1

      # Use stored limits if they exist, otherwise use role defaults
      db_limit = role_limits_map.get(role.roleId)
      if db_limit:
        role_min = db_limit.minDuration if db_limit.minDuration is not None else role_default_min
        role_max = db_limit.maxDuration if db_limit.maxDuration is not None else role_default_max
        role_active = db_limit.maxActiveReservations if db_limit.maxActiveReservations is not None else role_default_active
        lp_opinions.append(bool(db_limit.allowLowPriority))
      else:
        role_min, role_max, role_active = role_default_min, role_default_max, role_default_active

      # Use the lowest minimum duration (most permissive)
      if role_min < min_duration:
        min_duration = role_min

      # Use the highest maximum duration (most permissive)
      if role_max > max_duration:
        max_duration = role_max

      # Use the highest max active reservations (most permissive)
      if role_active > max_active_reservations:
        max_active_reservations = role_active

    # If no roles found, use defaults
    if min_duration == float('inf'):
      min_duration = default_min
    if max_duration == 0:
      max_duration = default_max
    if max_active_reservations == 0:
      max_active_reservations = default_active

    # Resolve low-priority permission:
    # - admins always allowed
    # - no explicit opinions from any role: allow (default-on for fresh installs)
    # - at least one explicit True: allow (most-permissive — a trusted role can re-enable)
    # - only explicit False values: deny
    if user_is_admin:
      allow_low_priority = True
    elif not lp_opinions:
      allow_low_priority = True
    else:
      allow_low_priority = any(lp_opinions)

    return {
      'minDuration': min_duration,
      'maxDuration': max_duration,
      'maxActiveReservations': max_active_reservations,
      'allowLowPriority': allow_low_priority
    }

def check_token(token : str) -> object:
  """Validate an authentication token and return user information.

  Checks the token against the database, verifies it has not expired based
  on the configured session timeout, and returns user details including
  roles and reservation limits.

  Args:
      token: The authentication token to validate.

  Returns:
      An api_response dict. On success, includes 'data' with userId, email,
      role (primary), roles (list), and reservationLimits. On failure,
      status is False with an error message.
  """
  if token == "" or token is None: return helpers.server.api_response(False, "Token cannot be empty.")

  def time_now(): return datetime.datetime.now(datetime.timezone.utc)
  from helpers.settings_handler import get_setting
  session_timeout = get_setting('auth.sessionTimeoutMinutes')
  min_start_date = time_now() - timedelta(minutes=session_timeout)

  # Materialize user data inside session scope
  user_data = None
  with Session() as session:
    user = session.execute(
      select(User).where(User.loginToken == token, User.loginTokenCreatedAt > min_start_date)
    ).scalar_one_or_none()
    if user is not None:
      user_data = {"userId": user.userId, "email": user.email, "name": user.name, "startScriptPath": user.startScriptPath, "stopScriptPath": user.stopScriptPath}

  if user_data is not None:
    user_role = get_role(user_data["email"])
    # Get all user roles
    user_role_names = []
    with Session() as session:
      from database import UserRole, Role
      user_roles = session.execute(select(Role).join(UserRole).where(UserRole.userId == user_data["userId"])).scalars().all()
      for role in user_roles:
        if role.name.lower() != 'everyone':  # Exclude 'everyone' role
          user_role_names.append(role.name)

    # Get user's reservation limits
    reservation_limits = get_user_reservation_limits(user_data["userId"])

    return helpers.server.api_response(True, "Token OK.", {
      "userId": user_data["userId"],
      "email": user_data["email"],
      "name": user_data["name"],
      "role": user_role,
      "roles": user_role_names,
      "reservationLimits": reservation_limits,
      "startScriptPath": user_data["startScriptPath"],
      "stopScriptPath": user_data["stopScriptPath"],
    })
  else:
    return helpers.server.api_response(False, "Invalid token.")

def get_authenticated_user_id(token: str) -> int:
  """Authenticate a token and return the associated user ID.

  Combines token validation and user ID extraction in a single call.

  Args:
      token: The authentication token.

  Returns:
      The authenticated user's database ID.

  Raises:
      HTTPException: 401 Unauthorized if the token is invalid or expired.
  """
  auth_result = check_token(token)
  if not auth_result["status"]:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail=auth_result["message"],
      headers={"WWW-Authenticate": "Bearer"},
    )
  return auth_result["data"]["userId"]

def create_login_token() -> str:
  """Generate a random login token of 100 characters.

  The token consists of lowercase and uppercase ASCII letters, digits,
  and the special characters '!', '_', and '-'.

  Returns:
      A 100-character random token string.
  """
  allowed_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + "!_-"
  limit = 100
  return ''.join(random.choice(allowed_chars) for _ in range(limit))

def hash_password(password: str) -> Tuple[bytes, bytes]:
  """Hash a password using PBKDF2-HMAC-SHA256 with a random salt.

  Args:
      password: The plaintext password to hash.

  Returns:
      A dict with 'salt' (bytes) and 'hashedPassword' (bytes) suitable
      for storing in the database.
  """
  salt = os.urandom(16)
  pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
  return { "salt": salt, "hashedPassword": pw_hash }

def is_correct_password(salt: bytes, pw_hash: bytes, password: str) -> bool:
  """Verify a password against a stored salt and hash.

  Uses constant-time comparison to prevent timing attacks.

  Args:
      salt: The salt bytes stored alongside the hash.
      pw_hash: The previously computed password hash.
      password: The plaintext password to verify.

  Returns:
      True if the password matches, False otherwise.
  """
  return hmac.compare_digest(
    pw_hash,
    hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
  )

def create_password(length = 40):
  """Generate a cryptographically secure random password.

  Args:
      length: The desired password length. Defaults to 40.

  Returns:
      A random string of ASCII letters and digits.
  """
  possible_chars = string.ascii_letters + string.digits
  random_password = "".join(secrets.choice(possible_chars) for _ in range(length))
  return random_password

def get_ldap_user(username, password):
  """Authenticate a user against the configured LDAP server.

  Attempts to bind to LDAP with the provided credentials, retrieves the
  user's email, and either returns an existing local user or creates a
  new one. Respects the whitelist setting if enabled.

  Args:
      username: The LDAP username to authenticate.
      password: The LDAP password.

  Returns:
      A tuple of (success, result) where:
          - On success: (True, userId) with the local user's database ID.
          - On failure: (False, error_message) with a descriptive error string.
  """
  from helpers.settings_handler import get_setting

  # Get LDAP settings from database
  ldap_url = get_setting('auth.ldap.url')
  username_format = get_setting('auth.ldap.usernameFormat')
  password_format = get_setting('auth.ldap.passwordFormat')
  ldap_domain = get_setting('auth.ldap.domain')
  search_method = get_setting('auth.ldap.searchMethod')
  account_field = get_setting('auth.ldap.accountField')
  email_field = get_setting('auth.ldap.emailField')
  name_field = get_setting('auth.ldap.nameField')

  # Check if LDAP is properly configured
  if not all([ldap_url, username_format, password_format, ldap_domain, search_method, account_field, email_field]):
    return False, "LDAP is not properly configured"

  use_whitelisting = get_setting('access.whitelistEnabled')
  # Disable certificate checks
  ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
  l = ldap.initialize(ldap_url)
  l.set_option(ldap.OPT_NETWORK_TIMEOUT, 6)
  l.set_option(ldap.OPT_TIMEOUT, 6)
  l.set_option(ldap.OPT_REFERRALS, ldap.OPT_OFF)

  with Session() as session:
    try:
      l.simple_bind_s(username_format.replace("{username}", username), password_format.replace("{password}", password))
      search_attrs = [account_field, email_field]
      if name_field:
        search_attrs.append(name_field)
      result = l.search_s(ldap_domain, ldap.SCOPE_SUBTREE, search_method.replace("{username}", username), search_attrs)
      account = result[0][1][account_field][0].decode("utf-8")
      if account != username:
        return False, "Wrong username / ldap username association"

      email = result[0][1][email_field][0].decode("utf-8")

      ldap_name = None
      if name_field and name_field in result[0][1]:
        ldap_name = result[0][1][name_field][0].decode("utf-8").strip()[:200]

      whitelist_email = session.execute(select(UserWhitelist).where(UserWhitelist.email == email)).scalar_one_or_none()
      if use_whitelisting and whitelist_email == None:
        return False, "You are not allowed to login (not whitelisted, LDAP)."

      user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
      # User not found? Create it and return the newly created user
      if user == None:
        new_user = User(
          email = email,
          name = ldap_name
        )
        session.add(new_user)
        session.commit()
        created_user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        from helpers.tables.audit_log import log_action
        log_action(created_user.userId, "USER_CREATE", "user", created_user.userId,
                   {"email": email, "source": "ldap"})
        return True, created_user.userId
      # User found? Update name from LDAP and return it
      else:
        if ldap_name is not None:
          user.name = ldap_name
          session.commit()
        return True, user.userId
    except ldap.INVALID_CREDENTIALS:
      return False, "Wrong username or password."
    except ldap.SERVER_DOWN:
      return False, "Failed to connect to LDAP authentication service: Timeout."
    except Exception:
      return False, "Unknown error with the LDAP login!"
