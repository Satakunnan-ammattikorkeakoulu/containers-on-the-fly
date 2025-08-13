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

class RoleHardwareLimitsEdit(BaseModel):
    '''
    For editing role hardware limits.
    '''
    roleId: int
    hardwareLimits: List[Dict[str, Any]]

class RoleReservationLimitsEdit(BaseModel):
    '''
    For editing role reservation limits.
    '''
    roleId: int
    reservationLimits: Dict[str, Any]