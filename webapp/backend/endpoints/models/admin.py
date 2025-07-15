from pydantic import BaseModel
from typing import Dict, Any, List

class ContainerEdit(BaseModel):
    '''
    For editing a container.
    '''
    containerId: int
    data: Dict[str, Any]

class ComputerEdit(BaseModel):
    '''
    For editing a computer.
    '''
    computerId: int
    data: Dict[str, Any]

class UserEdit(BaseModel):
    '''
    For editing a user.
    '''
    userId: int
    data: Dict[str, Any]

class RoleMountsEdit(BaseModel):
    '''
    For editing role mounts.
    '''
    roleId: int
    mounts: List[Dict[str, Any]]