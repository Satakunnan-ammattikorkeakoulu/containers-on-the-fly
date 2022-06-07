# Hardware specs table management functionality
from database import HardwareSpec, session

def getHardwarespecs(filter = None):
  '''
  Finds hardwarespecs with the given optional filter. If no filter is given, finds all hardwarespecs in the system.
    Parameters:
      filter: Additional filters. Example usage: ...
    Returns:
      All found hardwarespecs in a list.
  '''
  if filter != None:
    try:
      hardwarespecs = session.query(HardwareSpec).filter(HardwareSpec.hardwareSpecId == int(filter)).first()
      if hardwarespecs != None: return [hardwarespecs]
      else: return None
    except:
      return None
  else: hardwarespecs = session.query(HardwareSpec).all()
  return hardwarespecs

def addHardwarespec(computerId, type, maxAmount, minAmount, maxUserAmount, defaultUserAmount, format):
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
  newHardwarespec = HardwareSpec(computerId = computerId, type = type, maximumAmount = maxAmount, minimumAmount = minAmount, maximumAmountForUser = maxUserAmount, defaultAmountForUser = defaultUserAmount, format = format)
  session.add(newHardwarespec)
  session.commit()
  # So with the other ones, name was unique so I used it to return the new object, but the only unique field this has is it's own id
  # but I don't really know how to fetch the specific id since it doesnt exist until session.add so I'm not gonna return anything for now
  return #session.query(HardwareSpec).filter(HardwareSpec.name == name).first()

def removeHardwarespec(hardwarespec):
  '''
  Removes the given hardwarespec in the system.
    Parameters:
      hardwarespec: The hardwarespec object of the hardwarespec to be removed.
    Returns:
      Nothing
  '''
  session.delete(hardwarespec)
  session.commit()

#def editHardwarespec(hardwarespec, new_name = None, new_public = None, new_description = None, new_image_name = None):
def editHardwarespec(hardwarespec, new_computer, new_type, new_max, new_min, new_user_max, new_default, new_format):
  '''
  Edits the given hardwarespec in the system.
    Parameters:
      hardwarespec: The hardwarespec object of the hardwarespec to be edited.
      new_name: The new name for the given hardwarespec.
      new_public: The new boolean for publicity of the hardwarespec.
      new_description: The new description for the given hardwarespec.
      new_image_name: The new image name for the given hardwarespec.
    Returns:
      The edited hardwarespec object fetched from database. Or None if name or publicity isn't provided.
  '''
  if new_computer != None: hardwarespec.computerId = new_computer
  if new_type != None: hardwarespec.type = new_type
  if new_max != None: hardwarespec.maximumAmount = new_max
  if new_min != None: hardwarespec.minimumAmount = new_min
  if new_user_max != None: hardwarespec.maximumAmountForUser = new_user_max
  if new_default != None: hardwarespec.defaultAmountForUser = new_default
  if new_format != None: hardwarespec.format = new_format
  session.commit()
  return hardwarespec

#Database fields: 
#hardwareSpecId (PK), computerId (PK, FK), type, maximumAmount, minimumAmount, maximumAmountForUser, defaultAmountForUser, format, createdAt, updatedAt