"""Hardware specs table management functionality.

Provides CRUD operations for the HardwareSpec database table, including
lookup by ID, creation, deletion, and editing of hardware specification records
that define resource limits for container servers.
"""
from database import HardwareSpec, Session
from sqlalchemy import select

def get_hardware_specs(filter = None):
  """Find hardware specs with an optional filter.

  If no filter is given, returns all hardware specs. When a filter is
  provided, it attempts to match by hardware spec ID.

  Args:
      filter: A hardware spec ID (int-like) to search for. If None,
          all hardware specs are returned.

  Returns:
      A list of matching HardwareSpec objects, or None if a filter was
      provided but no match was found.
  """
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
  """Add a new hardware spec to the system.

  Args:
      computerId: The ID of the computer to associate with this hardware spec.
      type: The type of hardware (e.g. 'cpu', 'ram', 'gpu').
      maxAmount: The system-wide maximum amount of this hardware resource.
      minAmount: The minimum amount of this hardware resource.
      maxUserAmount: The maximum amount a single user can request.
      defaultUserAmount: The default amount allocated to a user.
      format: The unit format for the amounts (e.g. 'cores', 'GB').
  """
  new_hardware_spec = HardwareSpec(computerId = computerId, type = type, maximumAmount = maxAmount, minimumAmount = minAmount, maximumAmountForUser = maxUserAmount, defaultAmountForUser = defaultUserAmount, format = format)
  with Session() as session:
    session.add(new_hardware_spec)
    session.commit()
  return

def remove_hardware_spec(hardwarespec_id):
  """Remove a hardware spec from the system by its ID.

  Args:
      hardwarespec_id: The ID of the hardware spec to be removed.
  """
  with Session() as session:
    hardwarespec = session.execute(select(HardwareSpec).where(HardwareSpec.hardwareSpecId == hardwarespec_id)).scalar_one_or_none()
    session.delete(hardwarespec)
    session.commit()


def edit_hardware_spec(hardwarespec_id, new_computer_id, new_type, new_max, new_min, new_user_max, new_user_default, new_format):
  """Edit an existing hardware spec's attributes.

  Only the provided (non-None) fields are updated; others remain unchanged.

  Args:
      hardwarespec_id: The ID of the hardware spec to be edited.
      new_computer_id: The new computer ID, or None to keep current.
      new_type: The new hardware type, or None to keep current.
      new_max: The new system maximum amount, or None to keep current.
      new_min: The new minimum amount, or None to keep current.
      new_user_max: The new per-user maximum amount, or None to keep current.
      new_user_default: The new per-user default amount, or None to keep current.
      new_format: The new unit format, or None to keep current.

  Returns:
      The updated HardwareSpec object.
  """
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
