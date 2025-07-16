# Role table management functionality
from database import Role, RoleMount, Computer, Session, UserRole
from helpers.server import Response
from sqlalchemy import func

def getRoles():
    '''
    Gets all roles from the database.
    Returns:
        List of all roles.
    '''
    with Session() as session:
        return session.query(Role).all()

def getRolesWithMountCounts():
    '''
    Gets all roles from the database with their mount counts.
    Returns:
        List of all roles with additional mountCount field.
    '''
    with Session() as session:
        roles = session.query(Role).all()
        result = []
        for role in roles:
            from helpers.server import ORMObjectToDict
            role_dict = ORMObjectToDict(role)
            # Add mount count
            mount_count = session.query(RoleMount).filter(RoleMount.roleId == role.roleId).count()
            role_dict['mountCount'] = mount_count
            result.append(role_dict)
        return result

def getRoleById(roleId):
    '''
    Gets a role by its ID.
    Parameters:
        roleId: The ID of the role to get.
    Returns:
        The role object or None if not found.
    '''
    with Session() as session:
        return session.query(Role).filter(Role.roleId == roleId).first()

def isRoleNameTaken(session, name: str, excludeRoleId: int = None) -> bool:
    '''
    Checks if a role name is already taken.
    Parameters:
        session: The database session
        name: The name to check
        excludeRoleId: Optional role ID to exclude from the check (for updates)
    Returns:
        bool: True if name is taken, False otherwise
    '''
    query = session.query(Role).filter(func.lower(Role.name) == func.lower(name))
    if excludeRoleId is not None:
        query = query.filter(Role.roleId != excludeRoleId)
    return query.count() > 0

def validateRoleName(name: str) -> tuple[bool, str]:
    '''
    Validates a role name.
    Parameters:
        name: The name to validate
    Returns:
        tuple[bool, str]: (is_valid, error_message)
    '''
    # Check for reserved names (case insensitive)
    reserved_names = ["admin", "everyone"]
    if name.lower() in reserved_names:
        return False, f"The name '{name}' is reserved for built-in roles"
    return True, ""

def addRole(name: str) -> tuple[bool, str, dict]:
    '''
    Adds a new role to the database.
    Parameters:
        name: The name of the role
    Returns:
        tuple[bool, str, dict]: (success, message, role_dict)
    '''
    with Session() as session:
        try:
            # Validate name
            is_valid, error_msg = validateRoleName(name)
            if not is_valid:
                return False, error_msg, None

            # Check for duplicate names
            if isRoleNameTaken(session, name):
                return False, f"A role with the name '{name}' already exists", None

            # Create new role
            role = Role(name=name)
            session.add(role)
            session.commit()
            
            # Convert to dict while still in session
            from helpers.server import ORMObjectToDict
            role_dict = ORMObjectToDict(role)
            return True, "Role added successfully", role_dict

        except Exception as e:
            session.rollback()
            return False, f"Failed to add role: {str(e)}", None

def editRole(roleId: int, name: str) -> tuple[bool, str, dict]:
    '''
    Edits an existing role in the database.
    Parameters:
        roleId: The ID of the role to update
        name: The new name for the role
    Returns:
        tuple[bool, str, dict]: (success, message, role_dict)
    '''
    with Session() as session:
        try:
            # Validate name
            is_valid, error_msg = validateRoleName(name)
            if not is_valid:
                return False, error_msg, None

            # Check for duplicate names (excluding this role)
            if isRoleNameTaken(session, name, roleId):
                return False, f"A role with the name '{name}' already exists", None

            # Update existing role
            role = session.query(Role).filter(Role.roleId == roleId).first()
            if not role:
                return False, "Role not found", None
                
            role.name = name
            session.commit()
            
            # Convert to dict while still in session
            from helpers.server import ORMObjectToDict
            role_dict = ORMObjectToDict(role)
            return True, "Role updated successfully", role_dict

        except Exception as e:
            session.rollback()
            return False, f"Failed to update role: {str(e)}", None

def removeRole(roleId):
    '''
    Removes a role from the system and cleans up all associated data:
    - Removes all user associations (UserRole entries)
    - Removes all role mounts (RoleMount entries)
    - Removes the role itself
    
    Parameters:
        roleId: The ID of the role to remove.
    Returns:
        tuple[bool, str]: (success, message)
    '''
    with Session() as session:
        try:
            role = session.query(Role).filter(Role.roleId == roleId).first()
            if not role:
                return False, "Role not found"
            
            # Don't allow removing built-in roles
            if role.name.lower() in ["admin", "everyone"]:
                return False, f"Cannot remove built-in role '{role.name}'"
            
            # Remove all user associations
            session.query(UserRole).filter(UserRole.roleId == roleId).delete()
            
            # Remove all role mounts
            session.query(RoleMount).filter(RoleMount.roleId == roleId).delete()
            
            # Remove the role itself
            session.delete(role)
            session.commit()
            return True, "Role and all its associations removed successfully"
            
        except Exception as e:
            session.rollback()
            return False, f"Failed to remove role: {str(e)}"

def getRoleMounts(roleId: int) -> list:
    '''
    Gets all mounts for a specific role.
    Parameters:
        roleId: The ID of the role
    Returns:
        List of mount objects with computer information
    '''
    with Session() as session:
        role = session.query(Role).filter(Role.roleId == roleId).first()
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

def saveRoleMounts(roleId: int, mounts: list) -> tuple[bool, str]:
    '''
    Saves role mounts, removing old ones and adding new ones.
    Parameters:
        roleId: The ID of the role
        mounts: List of mount dictionaries with computerId, hostPath, containerPath, readOnly
    Returns:
        tuple[bool, str]: (success, message)
    '''
    with Session() as session:
        # Check if role exists
        role = session.query(Role).filter(Role.roleId == roleId).first()
        if not role:
            return False, "Role not found"
        
        # Remove all existing mounts for this role
        session.query(RoleMount).filter(RoleMount.roleId == roleId).delete()
        session.flush()
        
        # Add new mounts
        for mount_data in mounts:
            # Validate required fields
            if not all(key in mount_data for key in ['computerId', 'hostPath', 'containerPath']):
                return False, "Missing required mount fields"
                
            # Check if computer exists
            computer = session.query(Computer).filter(Computer.computerId == mount_data['computerId']).first()
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