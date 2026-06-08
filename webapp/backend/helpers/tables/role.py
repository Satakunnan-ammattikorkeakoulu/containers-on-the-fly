"""Role table management functionality.

Provides CRUD operations for the Role database table and related tables
(RoleMount, RoleHardwareLimit, RoleReservationLimit), including role
creation, editing, deletion, mount management, hardware limit management,
and reservation limit management.
"""
from database import Role, RoleMount, Computer, Session, UserRole
from helpers.server import api_response
from sqlalchemy import select, delete, func

def get_roles():
    """Get all roles from the database.

    Returns:
        A list of all Role ORM objects.
    """
    with Session() as session:
        return session.execute(select(Role)).scalars().all()

def get_roles_with_mount_counts():
    """Get all roles from the database with their mount counts.

    Returns:
        A list of role dictionaries, each augmented with a 'mountCount'
        field indicating how many RoleMount entries the role has.
    """
    with Session() as session:
        roles = session.execute(select(Role)).scalars().all()
        result = []
        for role in roles:
            from helpers.server import orm_to_dict
            role_dict = orm_to_dict(role)
            # Add mount count
            mount_count = session.execute(
                select(func.count()).select_from(RoleMount).where(RoleMount.roleId == role.roleId)
            ).scalar_one()
            role_dict['mountCount'] = mount_count
            result.append(role_dict)
        return result

def get_role_by_id(roleId):
    """Get a role by its ID.

    Args:
        roleId: The ID of the role to retrieve.

    Returns:
        The Role ORM object, or None if not found.
    """
    with Session() as session:
        return session.execute(select(Role).where(Role.roleId == roleId)).scalar_one_or_none()

def is_role_name_taken(session, name: str, excludeRoleId: int = None) -> bool:
    """Check if a role name is already taken (case-insensitive).

    Args:
        session: The active SQLAlchemy database session.
        name: The role name to check for uniqueness.
        excludeRoleId: An optional role ID to exclude from the check,
            used when updating a role to allow it to keep its own name.

    Returns:
        True if another role with the same name exists, False otherwise.
    """
    stmt = select(func.count()).select_from(Role).where(func.lower(Role.name) == func.lower(name))
    if excludeRoleId is not None:
        stmt = stmt.where(Role.roleId != excludeRoleId)
    return session.execute(stmt).scalar_one() > 0

def validate_role_name(name: str) -> tuple[bool, str]:
    """Validate a role name against naming rules.

    Checks that the name is non-empty and not a reserved name
    ('admin', 'everyone').

    Args:
        name: The role name to validate.

    Returns:
        A tuple of (is_valid, error_message). If valid, error_message
        is an empty string.
    """
    if not name or not name.strip():
        return False, "Role name is required"

    # Check for reserved names (case insensitive)
    reserved_names = ["admin", "everyone"]
    if name.lower() in reserved_names:
        return False, f"The name '{name}' is reserved for built-in roles"
    return True, ""

def add_role(name: str) -> tuple[bool, str, dict]:
    """Add a new role to the database.

    Validates the name and checks for duplicates before creating.

    Args:
        name: The name of the new role.

    Returns:
        A tuple of (success, message, role_dict). On success, role_dict
        contains the created role as a dictionary. On failure, role_dict
        is None.
    """
    with Session() as session:
        try:
            # Validate name
            is_valid, error_msg = validate_role_name(name)
            if not is_valid:
                return False, error_msg, None

            # Check for duplicate names
            if is_role_name_taken(session, name):
                return False, f"A role with the name '{name}' already exists", None

            # Create new role
            role = Role(name=name)
            session.add(role)
            session.commit()

            # Convert to dict while still in session
            from helpers.server import orm_to_dict
            role_dict = orm_to_dict(role)
            return True, "Role added successfully", role_dict

        except Exception as e:
            session.rollback()
            return False, f"Failed to add role: {str(e)}", None

def edit_role(roleId: int, name: str) -> tuple[bool, str, dict]:
    """Edit an existing role's name in the database.

    Validates the new name and checks for duplicates before updating.

    Args:
        roleId: The ID of the role to update.
        name: The new name for the role.

    Returns:
        A tuple of (success, message, role_dict). On success, role_dict
        contains the updated role as a dictionary. On failure, role_dict
        is None.
    """
    with Session() as session:
        try:
            # Validate name
            is_valid, error_msg = validate_role_name(name)
            if not is_valid:
                return False, error_msg, None

            # Check for duplicate names (excluding this role)
            if is_role_name_taken(session, name, roleId):
                return False, f"A role with the name '{name}' already exists", None

            # Update existing role
            role = session.execute(select(Role).where(Role.roleId == roleId)).scalar_one_or_none()
            if not role:
                return False, "Role not found", None

            role.name = name
            session.commit()

            # Convert to dict while still in session
            from helpers.server import orm_to_dict
            role_dict = orm_to_dict(role)
            return True, "Role updated successfully", role_dict

        except Exception as e:
            session.rollback()
            return False, f"Failed to update role: {str(e)}", None

def remove_role(roleId):
    """Remove a role and all its associated data from the system.

    Cleans up UserRole associations, RoleMount entries, and
    RoleHardwareLimit entries before deleting the role itself.
    Built-in roles ('admin', 'everyone') cannot be removed.

    Args:
        roleId: The ID of the role to remove.

    Returns:
        A tuple of (success, message).
    """
    with Session() as session:
        try:
            role = session.execute(select(Role).where(Role.roleId == roleId)).scalar_one_or_none()
            if not role:
                return False, "Role not found"

            # Don't allow removing built-in roles
            if role.name.lower() in ["admin", "everyone"]:
                return False, f"Cannot remove built-in role '{role.name}'"

            # Remove all user associations
            session.execute(delete(UserRole).where(UserRole.roleId == roleId))

            # Remove all role mounts
            session.execute(delete(RoleMount).where(RoleMount.roleId == roleId))

            # Remove all role hardware limits
            from database import RoleHardwareLimit
            session.execute(delete(RoleHardwareLimit).where(RoleHardwareLimit.roleId == roleId))

            # Remove the role itself
            session.delete(role)
            session.commit()
            return True, "Role and all its associations removed successfully"

        except Exception as e:
            session.rollback()
            return False, f"Failed to remove role: {str(e)}"

def get_role_mounts(roleId: int) -> list:
    """Get all mounts for a specific role.

    Args:
        roleId: The ID of the role to get mounts for.

    Returns:
        A list of mount dictionaries, each containing roleMountId,
        roleId, computerId, hostPath, containerPath, readOnly, and
        computerName fields. Returns an empty list if the role is
        not found.
    """
    with Session() as session:
        role = session.execute(select(Role).where(Role.roleId == roleId)).scalar_one_or_none()
        if not role:
            return []

        mounts = []
        for mount in role.mounts:
            mount_data = {
                "roleMountId": mount.roleMountId,
                "roleId": mount.roleId,
                "computerId": mount.computerId,
                "hostPath": mount.hostPath,
                "containerPath": mount.containerPath,
                "readOnly": mount.readOnly,
                "computerName": mount.computer.name if mount.computer else ""
            }
            mounts.append(mount_data)

        return mounts

def save_role_mounts(roleId: int, mounts: list) -> tuple[bool, str]:
    """Save role mounts by replacing all existing mounts with new ones.

    Deletes all current mounts for the role, then creates new entries
    from the provided list. Validates that each referenced computer exists.

    Args:
        roleId: The ID of the role to save mounts for.
        mounts: A list of mount dictionaries, each requiring 'computerId',
            'hostPath', and 'containerPath' keys. 'readOnly' is optional
            and defaults to False.

    Returns:
        A tuple of (success, message).
    """
    with Session() as session:
        # Check if role exists
        role = session.execute(select(Role).where(Role.roleId == roleId)).scalar_one_or_none()
        if not role:
            return False, "Role not found"

        # Remove all existing mounts for this role
        session.execute(delete(RoleMount).where(RoleMount.roleId == roleId))
        session.flush()

        # Add new mounts
        for mount_data in mounts:
            # Validate required fields
            if not all(key in mount_data for key in ['computerId', 'hostPath', 'containerPath']):
                return False, "Missing required mount fields"

            # Check if computer exists
            computer = session.execute(select(Computer).where(Computer.computerId == mount_data['computerId'])).scalar_one_or_none()
            if not computer:
                return False, f"Computer with ID {mount_data['computerId']} not found"

            new_mount = RoleMount(
                roleId=roleId,
                computerId=mount_data['computerId'],
                hostPath=mount_data['hostPath'],
                containerPath=mount_data['containerPath'],
                readOnly=mount_data.get('readOnly', False)
            )
            session.add(new_mount)

        session.commit()
        return True, "Role mounts saved successfully"

def get_role_hardware_limits(roleId: int) -> list:
    """Get hardware limits for a specific role.

    Args:
        roleId: The ID of the role to get hardware limits for.

    Returns:
        A list of hardware limit dictionaries, each containing
        roleHardwareLimitId, roleId, hardwareSpecId,
        maximumAmountForRole, computerId, and hardwareType fields.
    """
    from database import RoleHardwareLimit, HardwareSpec
    from helpers.server import orm_to_dict

    with Session() as session:
        limits = session.execute(
            select(RoleHardwareLimit)
            .where(RoleHardwareLimit.roleId == roleId)
            .join(HardwareSpec)
        ).scalars().all()

        result = []
        for limit in limits:
            limit_data = {
                "roleHardwareLimitId": limit.roleHardwareLimitId,
                "roleId": limit.roleId,
                "hardwareSpecId": limit.hardwareSpecId,
                "maximumAmountForRole": limit.maximumAmountForRole,
                "maximumAmountForRoleLowPriority": limit.maximumAmountForRoleLowPriority,
                "computerId": limit.hardwareSpec.computerId if limit.hardwareSpec else None,
                "hardwareType": limit.hardwareSpec.type if limit.hardwareSpec else None
            }
            result.append(limit_data)

        return result

def save_role_hardware_limits(roleId: int, hardwareLimits: list) -> tuple[bool, str]:
    """Save role hardware limits by replacing all existing limits with new ones.

    Deletes all current hardware limits for the role, then creates new
    entries from the provided list. Validates that each referenced hardware
    spec exists, that values are positive integers, and that role limits
    do not exceed system maximums. Built-in roles ('admin', 'everyone')
    cannot have hardware limits set.

    Args:
        roleId: The ID of the role to save hardware limits for.
        hardwareLimits: A list of hardware limit dictionaries, each
            requiring 'hardwareSpecId' and 'maximumAmountForRole' keys.
            Entries with None maximumAmountForRole are skipped.

    Returns:
        A tuple of (success, message).
    """
    from database import RoleHardwareLimit, HardwareSpec

    with Session() as session:
        # Check if role exists
        role = session.execute(select(Role).where(Role.roleId == roleId)).scalar_one_or_none()
        if not role:
            return False, "Role not found"

        # Prevent setting limits for built-in roles
        if role.name.lower() in ["admin", "everyone"]:
            return False, f"Cannot set hardware limits for built-in role '{role.name}'"

        # Remove all existing hardware limits for this role
        session.execute(delete(RoleHardwareLimit).where(RoleHardwareLimit.roleId == roleId))
        session.flush()

        # Add new hardware limits
        for limit_data in hardwareLimits:
            # Validate required fields
            if 'hardwareSpecId' not in limit_data:
                return False, "Missing required hardware limit fields"

            normal_value = limit_data.get('maximumAmountForRole')
            low_priority_value = limit_data.get('maximumAmountForRoleLowPriority')

            # Skip rows where neither normal nor low-priority override is set
            if normal_value is None and low_priority_value is None:
                continue

            # Check if hardware spec exists
            hardware_spec = session.execute(
                select(HardwareSpec).where(HardwareSpec.hardwareSpecId == limit_data['hardwareSpecId'])
            ).scalar_one_or_none()
            if not hardware_spec:
                return False, f"Hardware spec with ID {limit_data['hardwareSpecId']} not found"

            # For GPUs without internalId, system max is the count of all GPU specs
            if hardware_spec.type == 'gpu' and not hardware_spec.internalId:
                gpu_count = session.execute(
                    select(func.count()).select_from(HardwareSpec).where(
                        HardwareSpec.computerId == hardware_spec.computerId,
                        HardwareSpec.type == 'gpu'
                    )
                ).scalar_one()
                system_max = gpu_count
            else:
                system_max = hardware_spec.maximumAmount

            def _validate_value(value, label):
                """Coerce to int and enforce [0, system_max] bounds; return (value, error_message)."""
                if value is None:
                    return None, None
                if not isinstance(value, int):
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        return None, f"Invalid value for {label}: must be an integer, got '{value}'"
                if value < 0:
                    return None, f"{label} cannot be negative: {value}"
                if value > system_max:
                    return None, f"{label} ({value}) exceeds system maximum ({system_max}) for {hardware_spec.type} on computer {hardware_spec.computer.name}"
                return value, None

            normal_value, err = _validate_value(normal_value, "Hardware limit")
            if err:
                return False, err

            low_priority_value, err = _validate_value(low_priority_value, "Low-priority hardware limit")
            if err:
                return False, err

            new_limit = RoleHardwareLimit(
                roleId=roleId,
                hardwareSpecId=limit_data['hardwareSpecId'],
                maximumAmountForRole=normal_value,
                maximumAmountForRoleLowPriority=low_priority_value
            )
            session.add(new_limit)

        session.commit()
        return True, "Role hardware limits saved successfully"

def get_role_reservation_limits(roleId: int) -> dict:
    """Get reservation limits for a specific role, with defaults applied.

    Returns stored limits if they exist, otherwise returns sensible
    defaults. Admin roles get higher defaults (60-day max duration,
    99 active reservations) compared to regular roles (2-day max
    duration, 1 active reservation).

    Args:
        roleId: The ID of the role to get reservation limits for.

    Returns:
        A dictionary with 'minDuration', 'maxDuration', and
        'maxActiveReservations' keys (values in hours), or an empty
        dict if the role is not found.
    """
    from database import RoleReservationLimit

    with Session() as session:
        # Get role to check if it's admin
        role = session.execute(select(Role).where(Role.roleId == roleId)).scalar_one_or_none()
        if not role:
            return {}

        # Determine defaults based on role
        if role.name == "admin":
            default_min = 1  # 1 hour
            default_max = 1440  # 60 days (60 * 24 hours)
            default_active = 99
        else:
            default_min = 1  # 1 hour
            default_max = 48  # 48 hours (2 days)
            default_active = 1

        # Get existing limits
        limits = session.execute(
            select(RoleReservationLimit).where(RoleReservationLimit.roleId == roleId)
        ).scalar_one_or_none()

        if limits:
            return {
                "minDuration": limits.minDuration if limits.minDuration is not None else default_min,
                "maxDuration": limits.maxDuration if limits.maxDuration is not None else default_max,
                "lowPriorityMaxDuration": limits.lowPriorityMaxDuration,
                "allowLowPriority": limits.allowLowPriority,
                "maxActiveReservations": limits.maxActiveReservations if limits.maxActiveReservations is not None else default_active
            }
        else:
            # Return defaults when no database entry exists
            return {
                "minDuration": default_min,
                "maxDuration": default_max,
                "lowPriorityMaxDuration": None,
                "allowLowPriority": True,
                "maxActiveReservations": default_active
            }

def save_role_reservation_limits(roleId: int, reservationLimits: dict) -> tuple[bool, str]:
    """Save reservation limits for a role (create or update).

    Validates that all required fields are present and within allowed
    ranges: minDuration (1-720 hours), maxDuration (>= 1 hour, no upper
    bound so persistent workloads are possible), maxActiveReservations
    (0-99). Also ensures minDuration does not exceed maxDuration.

    Args:
        roleId: The ID of the role to save reservation limits for.
        reservationLimits: A dictionary with 'minDuration', 'maxDuration',
            and 'maxActiveReservations' keys (values in hours).

    Returns:
        A tuple of (success, message).
    """
    from database import RoleReservationLimit

    with Session() as session:
        # Check if role exists
        role = session.execute(select(Role).where(Role.roleId == roleId)).scalar_one_or_none()
        if not role:
            return False, "Role not found"

        # Get or create reservation limits
        limits = session.execute(
            select(RoleReservationLimit).where(RoleReservationLimit.roleId == roleId)
        ).scalar_one_or_none()

        if not limits:
            limits = RoleReservationLimit(roleId=roleId)
            session.add(limits)

        # Validate required fields
        if 'minDuration' not in reservationLimits or reservationLimits['minDuration'] is None:
            return False, "Minimum duration is required"
        if 'maxDuration' not in reservationLimits or reservationLimits['maxDuration'] is None:
            return False, "Maximum duration is required"
        if 'maxActiveReservations' not in reservationLimits or reservationLimits['maxActiveReservations'] is None:
            return False, "Max active reservations is required"

        # Update values
        limits.minDuration = reservationLimits['minDuration']
        limits.maxDuration = reservationLimits['maxDuration']
        limits.lowPriorityMaxDuration = reservationLimits.get('lowPriorityMaxDuration')
        if 'allowLowPriority' in reservationLimits and reservationLimits['allowLowPriority'] is not None:
            raw_allow = reservationLimits['allowLowPriority']
            if not isinstance(raw_allow, bool):
                return False, "allowLowPriority must be a boolean"
            limits.allowLowPriority = raw_allow
        limits.maxActiveReservations = reservationLimits['maxActiveReservations']

        # Validate min/max relationship
        if limits.minDuration > limits.maxDuration:
            return False, "Minimum duration cannot be greater than maximum duration"

        # Validate ranges
        if limits.minDuration < 1 or limits.minDuration > 720:
            return False, "Minimum duration must be between 1 and 720 hours"

        if limits.maxDuration < 1:
            return False, "Maximum duration must be at least 1 hour"

        if limits.lowPriorityMaxDuration is not None:
            if not isinstance(limits.lowPriorityMaxDuration, int):
                return False, "Low-priority maximum duration must be an integer"
            if limits.lowPriorityMaxDuration < 1:
                return False, "Low-priority maximum duration must be at least 1 hour"

        if limits.maxActiveReservations < 0 or limits.maxActiveReservations > 99:
            return False, "Max active reservations must be between 0 and 99"

        session.commit()
        return True, "Role reservation limits saved successfully"
