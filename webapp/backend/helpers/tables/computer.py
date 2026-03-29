# Computer table management functionality
from database import Computer, Session
from sqlalchemy import select

def get_computers(filter = None):
  '''
  Finds computers with the given optional filter. If no filter is given, finds all computers in the system.
    Parameters:
      filter: Additional filters. Example usage: ...
    Returns:
      All found computers in a list.
  '''
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
  '''
  Adds the given computer in the system.
    Parameters:
      name: The name of the computer to be added.
      public: Boolean. Whether the computer is public or not.
    Returns:
      The created computer object fetched from database. Or None if provided name already exists.
  '''
  with Session() as session:
    duplicate = session.execute(select(Computer).where(Computer.name == name)).scalar_one_or_none()
    if duplicate != None:
      return None
    new_computer = Computer(name = name, public = public)
    session.add(new_computer)
    session.commit()
    return session.execute(select(Computer).where(Computer.name == name)).scalar_one_or_none()

def remove_computer(computer_id):
  '''
  Removes the given computer in the system.
    Parameters:
      computer_id: The id of the computer to be removed.
    Returns:
      Nothing
  '''
  with Session() as session:
    computer = session.execute(select(Computer).where(Computer.computerId == computer_id)).scalar_one_or_none()
    session.delete(computer)
    session.commit()

def edit_computer(computer_id, new_name = None, new_public = None):
  '''
  Edits the given computer in the system.
    Parameters:
      computer_id: The id of the computer to be edited.
      new_name: The new name for the given computer.
      new_public: The new boolean for publicity of the computer.
    Returns:
      The edited computer object fetched from database. Or None if name or publicity isn't provided.
  '''
  with Session() as session:
    computer = session.execute(select(Computer).where(Computer.computerId == computer_id)).scalar_one_or_none()
    if new_name != None: computer.name = new_name
    if new_public != None: computer.public = new_public
    session.commit()
    return computer
