# Hardware specs table management functionality
from database import HardwareSpec, Session
from sqlalchemy import select

def get_hardware_specs(filter = None):
  '''
  Finds hardwarespecs with the given optional filter. If no filter is given, finds all hardwarespecs in the system.
    Parameters:
      filter: Additional filters. Example usage: ...
    Returns:
      All found hardwarespecs in a list.
  '''
  with Session() as session:
    if filter != None:
      try:
        hardwarespecs = session.execute(select(HardwareSpec).where(HardwareSpec.hardwareSpecId == int(filter))).scalar_one_or_none()
        if hardwarespecs != None: return [hardwarespecs]
        else: return None
      except:
        return None
    else: hardwarespecs = session.execute(select(HardwareSpec)).scalars().all()

    return hardwarespecs

def add_hardware_spec(computerId, type, maxAmount, minAmount, maxUserAmount, defaultUserAmount, format):
  '''
  Adds the given hardwarespec in the system.
    Parameters:
      computerId: The id of the computer to be associated with this hardware.
      type: The type of hardware.
      maxAmount: Maximum amount of this hardware.
      minAmount: Minimum amount of this hardware.
      maxUserAmount: The maximum amount of this hardware that a user can use.
      defaultUserAmount: User's default amount of this hardware.
      format: Format for the amounts.
    Returns:
      Nothing for now.
  '''
  new_hardware_spec = HardwareSpec(computerId = computerId, type = type, maximumAmount = maxAmount, minimumAmount = minAmount, maximumAmountForUser = maxUserAmount, defaultAmountForUser = defaultUserAmount, format = format)
  with Session() as session:
    session.add(new_hardware_spec)
    session.commit()
  return

def remove_hardware_spec(hardwarespec_id):
  '''
  Removes the given hardwarespec in the system.
    Parameters:
      hardwarespec_id: The id of the hardwarespec to be removed.
    Returns:
      Nothing
  '''
  with Session() as session:
    hardwarespec = session.execute(select(HardwareSpec).where(HardwareSpec.hardwareSpecId == hardwarespec_id)).scalar_one_or_none()
    session.delete(hardwarespec)
    session.commit()


def edit_hardware_spec(hardwarespec_id, new_computer_id, new_type, new_max, new_min, new_user_max, new_user_default, new_format):
  '''
  Edits the given hardwarespec in the system.
    Parameters:
      hardwarespec_id: The id of the hardwarespec to be edited.
      new_name: The new name for the given hardwarespec.
      new_public: The new boolean for publicity of the hardwarespec.
      new_description: The new description for the given hardwarespec.
      new_image_name: The new image name for the given hardwarespec.
    Returns:
      The edited hardwarespec object fetched from database. Or None if name or publicity isn't provided.
  '''
  with Session() as session:
    hardwarespec = session.execute(select(HardwareSpec).where(HardwareSpec.hardwareSpecId == hardwarespec_id)).scalar_one_or_none()
    if new_computer_id != None: hardwarespec.computerId = new_computer_id
    if new_type != None: hardwarespec.type = new_type
    if new_max != None: hardwarespec.maximumAmount = new_max
    if new_min != None: hardwarespec.minimumAmount = new_min
    if new_user_max != None: hardwarespec.maximumAmountForUser = new_user_max
    if new_user_default != None: hardwarespec.defaultAmountForUser = new_user_default
    if new_format != None: hardwarespec.format = new_format
    session.commit()
    return hardwarespec
