"""Server helper utilities for API responses and authentication enforcement.

Provides the standard API response wrapper, authentication enforcement for
endpoints, and ORM-to-dict conversion for SQLAlchemy models.
"""

from typing import Union
from fastapi import HTTPException, status
from sqlalchemy import inspect, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import joinedload
from helpers.auth import *
from database import User, Session
from settings_handler import settings_handler

def api_response(status, message, extra_data = None):
  """Build a standardized API response dict.

  All endpoint response functions should use this to ensure a consistent
  response format across the API.

  Args:
      status: Boolean indicating success (True) or failure (False).
      message: A human-readable message describing the result.
      extra_data: Optional additional data to include under the 'data' key.

  Returns:
      A dict with 'status', 'message', and optionally 'data' keys.
  """
  response = {
    "status": status,
    "message": message
  }
  if extra_data is not None:
    response["data"] = extra_data
  return response

def force_authentication(token: str, role_required: str = None) -> Union[bool,HTTPException]:
  """Enforce authentication and optionally verify a required role.

  Validates the user's token and, if a role is specified, checks that the
  user has that role assigned. For admin role checks, uses the is_admin()
  function. For other roles, checks both the primary role and the full
  roles list.

  Args:
      token: The authentication bearer token.
      role_required: An optional role name the user must have (e.g. 'admin').

  Returns:
      True if the user is authenticated and has the required role.

  Raises:
      HTTPException: 401 Unauthorized if the token is invalid or the user
          does not have the required role.
  """
  wrong_role = False
  if (is_logged_in(token)):
    if role_required is not None:
      # Materialize user data inside session scope
      with Session() as session:
        user = session.execute(
          select(User).options(joinedload(User.roles)).where(User.loginToken == token)
        ).unique().scalar_one_or_none()
        user_id = user.userId if user else None
        user_email = user.email if user else None
        user_role_names = [role.name for role in user.roles] if user else []
      # Check if user has the required role
      if role_required == "admin":
        # Use is_admin function which properly checks all roles
        if is_admin(user_id):
          return True
        else:
          wrong_role = True
      else:
        # For non-admin roles, check if it's the primary role or in the roles list
        if get_role(user_email) == role_required:
          return True
        else:
          # Also check if the role is in user's roles list
          has_role = False
          for role_name in user_role_names:
            if role_name == role_required:
              has_role = True
              break
          if has_role:
            return True
          else:
            wrong_role = True
    else:
      return True

  detail_message = "Invalid authentication credentials"
  if wrong_role == True:
    detail_message = detail_message + " - Wrong role"
  raise HTTPException(
    status_code = status.HTTP_401_UNAUTHORIZED,
    detail = detail_message,
    headers = {"WWW-Authenticate": "Bearer"},
  )

def orm_to_dict(self):
    """Convert a SQLAlchemy ORM model instance to a plain dictionary.

    Iterates over all mapped columns and hybrid properties, converting
    bytes values to strings. Skips columns whose names start with '_'.

    Args:
        self: The SQLAlchemy ORM model instance.

    Returns:
        A dict mapping column/property names to their values.
    """
    result = {}
    for key in self.__mapper__.c.keys():
        # Going through all the keys one by one
        if not key.startswith('_'):
            # Cast all bytes to strings
            if isinstance(getattr(self, key), bytes):
              result[key] = str(getattr(self, key))
            # Otherwise do the casting automatically
            else:
              result[key] = getattr(self, key)

    for key, prop in inspect(self.__class__).all_orm_descriptors.items():
        if isinstance(prop, hybrid_property):
            result[key] = getattr(self, key)
    return result
