# Role table management functionality
from database import Role, Session
from helpers.server import Response

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

def addRole(name):
    '''
    Adds a new role to the system.
    Parameters:
        name: The name of the role.
    Returns:
        The created role object or None if name already exists.
    '''
    with Session() as session:
        # Check if role with this name already exists
        existing = session.query(Role).filter(Role.name == name).first()
        if existing:
            return None
            
        newRole = Role(name=name)
        session.add(newRole)
        session.commit()
        return session.query(Role).filter(Role.name == name).first()

def editRole(roleId, name):
    '''
    Edits an existing role.
    Parameters:
        roleId: The ID of the role to edit.
        name: The new name for the role.
    Returns:
        True if successful, False if role not found or name already exists.
    '''
    with Session() as session:
        # Don't allow editing built-in roles
        if roleId <= 1:
            return False
            
        # Check if new name already exists
        existing = session.query(Role).filter(Role.name == name).first()
        if existing and existing.roleId != roleId:
            return False
            
        role = session.query(Role).filter(Role.roleId == roleId).first()
        if not role:
            return False
            
        role.name = name
        session.commit()
        return True

def removeRole(roleId):
    '''
    Removes a role from the system.
    Parameters:
        roleId: The ID of the role to remove.
    Returns:
        True if successful, False if role not found or is built-in.
    '''
    with Session() as session:
        # Don't allow removing built-in roles
        if roleId <= 1:
            return False
            
        role = session.query(Role).filter(Role.roleId == roleId).first()
        if not role:
            return False
            
        session.delete(role)
        session.commit()
        return True