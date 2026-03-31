"""User table management functionality.

Provides CRUD operations for the User database table, including lookup
by email or user ID, creation, deletion, editing, and conversion of
User ORM objects to dictionaries.
"""
from database import User, Session
from helpers.auth import *
from sqlalchemy import select

def get_users(email = None):
  """Find users with an optional email filter.

  If no email is given, returns all users. When an email is provided,
  performs a partial match (LIKE) search against user email addresses.

  Args:
      email: A partial or full email string to search for. If None,
          all users are returned.

  Returns:
      A list of user dictionaries (via cast_users_to_dict), or None
      if an email filter was provided but no match was found.
  """
  with Session() as session:
    all_users_list = []
    email_users_list = []
    if email is None:
      all_users = session.execute(select(User)).scalars().all()
      all_users = cast_users_to_dict(all_users)
      return all_users
    else:
      email_users = session.execute(select(User).where(User.email.like("%"+email+"%"))).scalars().all()
      if email_users != None:
        for email_user in email_users:
          email_users_list.append(email_user)
        email_users_list = cast_users_to_dict(email_users_list)
        return email_users_list
      else:
        return None

def get_user(findby):
  """Find a single user by email or user ID.

  Attempts to match by email first, then falls back to matching by userId.

  Args:
      findby: An email address or user ID to search for. If falsy,
          returns None.

  Returns:
      A list of user dictionaries (via cast_users_to_dict) containing
      the matched user, or None if no user was found.
  """
  with Session() as session:
    if findby:
      found_user = session.execute(select(User).where(User.email == findby)).scalar_one_or_none()
      if found_user:
        found_user = cast_users_to_dict([found_user])
        return found_user
      found_user = session.execute(select(User).where(User.userId == findby)).scalar_one_or_none()
      if found_user:
        found_user = cast_users_to_dict([found_user])
        return found_user
    else:
      return None

def cast_users_to_dict(user_list):
  """Convert a list of User ORM objects to a list of dictionaries.

  Args:
      user_list: A list of User ORM objects to convert.

  Returns:
      A list of dictionaries, each containing userId, email,
      userCreatedAt, userUpdatedAt, roles, reservations, and
      userStorage fields.
  """
  all_users = [dict(userId = user.userId, email = user.email, userCreatedAt = user.userCreatedAt, userUpdatedAt = user.userUpdatedAt, roles = user.roles, reservations = user.reservations, userStorage = user.userStorage) for user in user_list]
  return all_users

def add_user(email, password):
  """Add a new user to the system.

  The password is hashed with a generated salt before storage.

  Args:
      email: The email address for the new user.
      password: The plaintext password to be hashed and stored.
  """
  hash = hash_password(password)
  with Session() as session:
    session.add(
      User(
        email = email,
        password = hash["hashedPassword"],
        passwordSalt = hash["salt"]
      )
    )
    session.commit()

def edit_user(email, new_email = None, new_password = None):
  """Edit an existing user's email or password.

  Only the provided (non-None) fields are updated; others remain unchanged.

  Args:
      email: The current email address of the user to edit.
      new_email: The new email address, or None to keep current.
      new_password: The new plaintext password to hash and store,
          or None to keep current.

  Returns:
      None.
  """
  if email is None:
    return None

  with Session() as session:
    user = get_user_serverside(email)
    if new_email != None:
      user.email = new_email
    if new_password != None:
      hash = hash_password(new_password)
      user.password = hash["hashedPassword"]
      user.passwordSalt = hash['salt']
    session.commit()
    return None

def remove_user(findby):
  """Remove a user from the system.

  Looks up the user server-side before deleting.

  Args:
      findby: An email address or user ID identifying the user to remove.
  """
  with Session() as session:
    found_user = get_user_serverside(findby)
    session.delete(found_user)
    session.commit()

def get_user_serverside(search):
  """Find a user by email or user ID, returning the raw ORM object.

  Unlike get_user(), this returns the SQLAlchemy User object directly
  (not converted to a dict) and is intended for server-side operations
  such as editing or deleting.

  Args:
      search: An email address or user ID to search for. If None,
          returns None.

  Returns:
      The User ORM object if found, or None if no match exists.
  """
  with Session() as session:
    if search != None:
      roles = session.execute(select(User).where(User.email == search)).scalar_one_or_none()
      if roles != None: return roles
      else:
        try:
          roles = session.execute(select(User).where(User.userId == int(search))).scalar_one_or_none()
          if roles != None: return roles
          else:
            return None
        except:
          return None
    else:
      return None
