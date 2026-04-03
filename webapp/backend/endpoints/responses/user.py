"""Response handlers for user authentication and profile endpoints.

Provides login (password, LDAP, and hybrid authentication), token validation,
password management, profile retrieval, SSH key management, and container
lifecycle script path management for users.
"""

from database import User, Session, UserWhitelist, UserBlacklist
from helpers.settings_handler import get_setting
from helpers.server import api_response
from helpers.auth import create_login_token, hash_password, is_correct_password, check_token, get_ldap_user, get_role
from helpers.tables.audit_log import log_action
from fastapi import HTTPException, status
from datetime import datetime, timezone
from sqlalchemy import select
import base64
import re

def login(username, password):
  """Authenticate a user using the configured authentication method.

  Supports password-only, LDAP-only, and hybrid (password-then-LDAP)
  authentication. Checks blacklist/whitelist access controls before
  attempting authentication. On success, generates and stores a login
  token for session management.

  Args:
      username: The user's email address.
      password: The user's password.

  Returns:
      On success, a dict with access_token and token_type for bearer auth.
      On failure, a Response indicating invalid credentials or access denial.

  Raises:
      HTTPException: If username or password is empty, user is not found,
          password is not set, or credentials are incorrect.
  """
  if username == "" or username is None: raise HTTPException(status_code=400, detail="username cannot be empty.")
  if password == "" or password is None: raise HTTPException(status_code=400, detail="password cannot be empty.")

  with Session() as session:
    # Get auth settings from database
    login_type = get_setting('auth.loginType')
    use_whitelisting = get_setting('access.whitelistEnabled')
    use_blacklisting = get_setting('access.blacklistEnabled')

    # Look up user by email first for any auth type
    user = session.execute(select(User).where(User.email == username)).scalar_one_or_none()

    # Check blacklist first - this overrides whitelist and denies access immediately
    if use_blacklisting:
      blacklist_email = session.execute(select(UserBlacklist).where(UserBlacklist.email == username)).scalar_one_or_none()
      if blacklist_email is not None:
        log_action(None, "LOGIN_FAILED", "user", details={"email": username, "reason": "blacklisted"})
        return api_response(False, "You are not allowed to login (blacklisted).")

    # Check whitelist if enabled
    if use_whitelisting:
      whitelist_email = session.execute(select(UserWhitelist).where(UserWhitelist.email == username)).scalar_one_or_none()
      if whitelist_email is None:
        log_action(None, "LOGIN_FAILED", "user", details={"email": username, "reason": "not whitelisted"})
        return api_response(False, "You are not allowed to login (not whitelisted).")

    # Helper function to create login token
    def create_successful_login(user):
      user.loginToken = create_login_token()
      user.loginTokenCreatedAt = datetime.now(timezone.utc)
      session.commit()
      log_action(user.userId, "LOGIN", "user")
      return {
        "access_token": user.loginToken,
        "token_type": "bearer"
      }

    # Try password authentication
    def try_password_auth():
      # Check if user exists and has password set
      if not user:
        log_action(None, "LOGIN_FAILED", "user", details={"email": username, "reason": "user not found"})
        raise HTTPException(status_code=400, detail="User not found.")

      if user.password == "" or user.password is None:
        log_action(user.userId, "LOGIN_FAILED", "user", details={"email": username, "reason": "no password set"})
        raise HTTPException(status_code=400, detail="User password was not set yet. Please set the password first to login.")

      if is_correct_password(base64.b64decode(user.passwordSalt), base64.b64decode(user.password), password) == False:
        log_action(user.userId, "LOGIN_FAILED", "user", details={"email": username, "reason": "incorrect password"})
        raise HTTPException(status_code=400, detail="Incorrect password.")

      # Password is correct
      return create_successful_login(user)

    # Try LDAP authentication
    def try_ldap_auth():
      ldap_success, response = get_ldap_user(username, password)
      if ldap_success == False:
        return api_response(False, response)

      # Get or create user
      ldap_user = session.execute(select(User).where(User.userId == response)).scalar_one_or_none()
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
  """Validate a user's authentication token.

  Checks that the given token exists, belongs to an active user, and
  has not expired based on the configured session timeout.

  Args:
      token: The bearer token to validate.

  Returns:
      A dict with status True and user information if the token is valid.

  Raises:
      HTTPException: 401 Unauthorized if the token is invalid or expired.
  """
  token_check = check_token(token)

  if (token_check["status"] == True): return token_check
  else:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid authentication credentials",
      headers={"WWW-Authenticate": "Bearer"},
    )

def create_password(password):
  """Generate an encrypted password hash and salt for a user.

  Args:
      password: The plaintext password to hash.

  Returns:
      Response with the base64-encoded hashed password and salt,
      or an error response if the password is empty.
  """
  if password == "" or password is None:
    return api_response(False, "Password cannot be empty.")
  hash = hash_password(password)
  return api_response(True, "Password created", {
    "password": str(hash["hashedPassword"]),
    "salt": str(hash['salt'])
  })

def profile(token):
  """Retrieve the authenticated user's profile information.

  Args:
      token: The user's login token.

  Returns:
      Response with user details including userId, email, createdAt,
      role, and sshPublicKey, or an error if the user is not found.
  """
  with Session() as session:
    user = session.execute(select(User).where(User.loginToken == token)).scalar_one_or_none()
    if user is None: return api_response(False, "User not found.")
    else:
      user_details = {}
      user_details["userId"] = user.userId
      user_details["email"] = user.email
      user_details["name"] = user.name
      user_details["createdAt"] = user.userCreatedAt
      user_details["role"] = get_role(user.email)
      user_details["sshPublicKey"] = user.sshPublicKey
      user_details["startScriptPath"] = user.startScriptPath
      user_details["stopScriptPath"] = user.stopScriptPath
      return api_response(True, "User details found", { "user": user_details })

def has_password(token):
  """Check whether the authenticated user has a password set.

  Args:
      token: The user's login token.

  Returns:
      Response with hasPassword boolean indicating whether the user
      has a non-empty password, or an error if the user is not found.
  """
  with Session() as session:
    user = session.execute(select(User).where(User.loginToken == token)).scalar_one_or_none()
    if user is None:
      return api_response(False, "User not found.")

    # Check if password is set (not None and not empty string)
    has_password_set = user.password is not None and user.password != ""
    return api_response(True, "Password status checked", {"hasPassword": has_password_set})

def change_password(token, current_password, new_password):
  """Change the authenticated user's password.

  Verifies the current password before setting the new one. The new
  password must be at least 5 characters long and the user must already
  have a password set (LDAP-only users cannot change passwords here).

  Args:
      token: The user's login token.
      current_password: The user's current password for verification.
      new_password: The desired new password.

  Returns:
      Response indicating success or failure with an appropriate message.
  """
  if current_password == "" or current_password is None:
    return api_response(False, "Current password cannot be empty.")
  if new_password == "" or new_password is None:
    return api_response(False, "New password cannot be empty.")
  if len(new_password) < 5:
    return api_response(False, "New password must be at least 5 characters long.")

  with Session() as session:
    user = session.execute(select(User).where(User.loginToken == token)).scalar_one_or_none()
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

def update_ssh_key(token, ssh_public_key):
  """Update or remove the authenticated user's SSH public key.

  Validates that each non-comment line starts with a recognized SSH key
  prefix (ssh-rsa, ssh-ed25519, ecdsa-sha2-, ssh-dss). Supports
  multi-line key input. Pass None or empty string to remove the key.

  Args:
      token: The user's login token.
      ssh_public_key: The SSH public key string to store, or None/empty
          to remove the existing key.

  Returns:
      Response indicating success or failure with an appropriate message.
  """
  with Session() as session:
    user = session.execute(select(User).where(User.loginToken == token)).scalar_one_or_none()
    if user is None:
      return api_response(False, "User not found.")

    if ssh_public_key and ssh_public_key.strip():
      ssh_public_key = ssh_public_key.strip()
      valid_prefixes = ('ssh-rsa', 'ssh-ed25519', 'ssh-dss', 'ecdsa-sha2-')
      # Validate each non-empty line is a valid SSH key or a comment
      for line in ssh_public_key.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
          continue
        if not any(line.startswith(p) for p in valid_prefixes):
          return api_response(False, "Invalid SSH public key format. Each key line should start with ssh-rsa, ssh-ed25519, ecdsa-sha2-, or ssh-dss.")
      user.sshPublicKey = ssh_public_key
    else:
      user.sshPublicKey = None

    session.commit()
    return api_response(True, "SSH public key updated successfully.")

SCRIPT_PATH_REGEX = re.compile(r'^/[a-zA-Z0-9._/\-]+$')

def validate_script_path(path):
  """Validate a container script path.

  Args:
      path: The script path string to validate.

  Returns:
      str or None: Error message if invalid, None if valid.
  """
  if len(path) > 500:
    return "Script path must be 500 characters or less."
  if not SCRIPT_PATH_REGEX.match(path):
    return "Script path must be an absolute path starting with / and contain only alphanumeric characters, dots, underscores, slashes, and hyphens."
  return None

def update_script_paths(token, start_script_path, stop_script_path):
  """Update or remove the authenticated user's container lifecycle script paths.

  Validates that each path is an absolute path with safe characters.
  Pass None or empty string to remove a script path.

  Args:
      token: The user's login token.
      start_script_path: Absolute path to a start script inside the container,
          or None/empty to remove.
      stop_script_path: Absolute path to a stop script inside the container,
          or None/empty to remove.

  Returns:
      Response indicating success or failure with an appropriate message.
  """
  with Session() as session:
    user = session.execute(select(User).where(User.loginToken == token)).scalar_one_or_none()
    if user is None:
      return api_response(False, "User not found.")

    if start_script_path and start_script_path.strip():
      start_script_path = start_script_path.strip()
      error = validate_script_path(start_script_path)
      if error:
        return api_response(False, f"Start script path: {error}")
      user.startScriptPath = start_script_path
    else:
      user.startScriptPath = None

    if stop_script_path and stop_script_path.strip():
      stop_script_path = stop_script_path.strip()
      error = validate_script_path(stop_script_path)
      if error:
        return api_response(False, f"Stop script path: {error}")
      user.stopScriptPath = stop_script_path
    else:
      user.stopScriptPath = None

    session.commit()
    return api_response(True, "Script paths updated successfully.")

def update_name(token, name):
  """Update or remove the authenticated user's display name.

  Args:
      token: The user's login token.
      name: The display name to store, or None/empty to remove.

  Returns:
      Response indicating success or failure with an appropriate message.
  """
  with Session() as session:
    user = session.execute(select(User).where(User.loginToken == token)).scalar_one_or_none()
    if user is None:
      return api_response(False, "User not found.")

    if name and name.strip():
      name = name.strip()
      if len(name) > 200:
        return api_response(False, "Name must be 200 characters or less.")
      user.name = name
    else:
      user.name = None

    session.commit()
    return api_response(True, "Name updated successfully.")
