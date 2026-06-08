"""Computer table management functionality.

Provides CRUD operations for the Computer database table, including
lookup by name or ID, creation, deletion, and editing of computer
(container server) records.
"""
from database import Computer, Session
from sqlalchemy import select

def get_computers(filter = None):
  """Find computers with an optional filter.

  If no filter is given, returns all computers. When a filter is provided,
  it first attempts to match by computer name, then by computer ID.

  Args:
      filter: A computer name (str) or computer ID (int-like str) to
          search for. If None, all computers are returned.

  Returns:
      A list of matching Computer objects, or None if a filter was
      provided but no match was found.
  """
  with Session() as session:
    if filter != None:
      computers = session.execute(select(Computer).where(Computer.name == filter)).scalar_one_or_none()
      if computers != None: return [computers]
      else:
        try:
          computers = session.execute(select(Computer).where(Computer.computerId == int(filter))).scalar_one_or_none()
          if computers != None: return [computers]
          else: return None
        except:
          return None
    else: computers = session.execute(select(Computer)).scalars().all()
    return computers

def add_computer(name, public):
  """Add a new computer to the system.

  Args:
      name: The name of the computer to be added.
      public: Whether the computer is publicly visible.

  Returns:
      The created Computer object fetched from the database, or None
      if a computer with the given name already exists.
  """
  with Session() as session:
    duplicate = session.execute(select(Computer).where(Computer.name == name)).scalar_one_or_none()
    if duplicate != None:
      return None
    new_computer = Computer(name = name, public = public)
    session.add(new_computer)
    session.commit()
    return session.execute(select(Computer).where(Computer.name == name)).scalar_one_or_none()

def remove_computer(computer_id):
  """Remove a computer from the system by its ID.

  Args:
      computer_id: The ID of the computer to be removed.
  """
  with Session() as session:
    computer = session.execute(select(Computer).where(Computer.computerId == computer_id)).scalar_one_or_none()
    session.delete(computer)
    session.commit()

def edit_computer(computer_id, new_name = None, new_public = None):
  """Edit an existing computer's attributes.

  Only the provided (non-None) fields are updated; others remain unchanged.

  Args:
      computer_id: The ID of the computer to be edited.
      new_name: The new name for the computer, or None to keep current.
      new_public: The new public visibility flag, or None to keep current.

  Returns:
      The updated Computer object.
  """
  with Session() as session:
    computer = session.execute(select(Computer).where(Computer.computerId == computer_id)).scalar_one_or_none()
    if new_name != None: computer.name = new_name
    if new_public != None: computer.public = new_public
    session.commit()
    return computer
