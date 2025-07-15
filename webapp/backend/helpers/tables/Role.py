# Role table management functionality
from database import Role, Session
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
    Removes a role from the system.
    Parameters:
        roleId: The ID of the role to remove.
    Returns:
        tuple[bool, str]: (success, message)
    '''
    with Session() as session:
        # Don't allow removing built-in roles
        if roleId <= 1:
            return False, "Cannot remove built-in roles"
            
        role = session.query(Role).filter(Role.roleId == roleId).first()
        if not role:
            return False, "Role not found"
            
        session.delete(role)
        session.commit()
        return True, "Role removed successfully"