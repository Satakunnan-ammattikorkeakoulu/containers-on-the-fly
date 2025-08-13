from fastapi import APIRouter, Depends, Request
from helpers.server import ForceAuthentication, Response
from fastapi.security import OAuth2PasswordBearer
from endpoints.responses import admin as functionality
from endpoints.models.admin import ContainerEdit, ComputerEdit, UserEdit, RoleMountsEdit, RoleHardwareLimitsEdit, RoleReservationLimitsEdit
from endpoints.models.reservation import ReservationFilters
from database import Session, Computer, ContainerPort, User, Reservation, Container, ReservedContainer, ReservedHardwareSpec, HardwareSpec, UserRole, ServerStatus, ServerLogs
from sqlalchemy import desc, Column, Integer, Text, Float, ForeignKey, DateTime, UniqueConstraint, Boolean, BigInteger, func
import datetime
from pydantic import BaseModel
from helpers.tables.Role import getRoles, getRoleById, addRole as addRoleHelper, editRole as editRoleHelper, removeRole as removeRoleHelper
from helpers.server import Response, ORMObjectToDict
from typing import Dict, Any, List

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    responses={404: {"description": "Not found"}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")  # Make sure the tokenUrl is correct

@router.post("/reservations")
async def getReservations(filters : ReservationFilters, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getReservations(filters)

@router.get("/users")
async def getUsers(token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getUsers()

@router.get("/hardware")
async def getHardware(token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getHardware()

@router.get("/containers")
async def getContainers(token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getContainers()

@router.get("/computers")
async def getComputers(token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getComputers()

@router.get("/computer")
async def getComputer(computerId : int, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getComputer(computerId)

@router.post("/save_computer")
async def saveComputer(computerEdit : ComputerEdit, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.saveComputer(computerEdit)

@router.post("/remove_computer")
async def removeComputer(computerId : int, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.removeComputer(computerId)

@router.get("/container")
async def getContainer(containerId : int, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getContainer(containerId)

@router.post("/save_container")
async def saveContainer(containerEdit : ContainerEdit, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.saveContainer(containerEdit)

@router.post("/remove_container")
async def removeContainer(containerId : int, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.removeContainer(containerId)

@router.post("/edit_reservation")
async def editReservation(reservationId : int, endDate : str, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.editReservation(reservationId, endDate)

@router.get("/user")
async def getUser(userId: int, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.getUser(userId)

@router.post("/save_user")
async def saveUser(userEdit: UserEdit, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.saveUser(userEdit.userId, userEdit.data)

@router.get("/roles")
async def getRoles(token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.getAllRoles()

@router.post("/save_role")
async def saveRole(roleId: int = None, name: str = None, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    if roleId:
        return functionality.editRole(roleId, name)
    else:
        return functionality.addRole(name)

@router.post("/remove_role")
async def removeRole(roleId: int, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.removeRole(roleId)

@router.get("/role_mounts")
async def getRoleMounts(roleId: int, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.getRoleMounts(roleId)

@router.post("/save_role_mounts")
async def saveRoleMounts(roleMountsEdit: RoleMountsEdit, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.saveRoleMounts(roleMountsEdit.roleId, roleMountsEdit.mounts)

@router.get("/role_hardware_limits")
async def getRoleHardwareLimits(roleId: int, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.getRoleHardwareLimits(roleId)

@router.post("/save_role_hardware_limits")
async def saveRoleHardwareLimits(roleHardwareLimitsEdit: RoleHardwareLimitsEdit, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.saveRoleHardwareLimits(roleHardwareLimitsEdit.roleId, roleHardwareLimitsEdit.hardwareLimits)

@router.get("/role_reservation_limits")
async def getRoleReservationLimits(roleId: int, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.getRoleReservationLimits(roleId)

@router.post("/save_role_reservation_limits")
async def saveRoleReservationLimits(roleReservationLimitsEdit: RoleReservationLimitsEdit, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.saveRoleReservationLimits(roleReservationLimitsEdit.roleId, roleReservationLimitsEdit.reservationLimits)

@router.get("/server/{computer_id}/monitoring")
async def getServerMonitoring(computer_id: int, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.getServerMonitoring(computer_id)

@router.get("/servers")
async def getServersForMonitoring(token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.getServersForMonitoring()

# General admin settings endpoints
class GeneralSettingsData(BaseModel):
    section: str
    settings: Dict[str, Any]

class TestEmailData(BaseModel):
    email: str

@router.get("/general-settings")
async def getGeneralSettings(token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.getGeneralSettings()

@router.post("/general-settings")
async def saveGeneralSettings(data: GeneralSettingsData, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.saveGeneralSettings(data.section, data.settings)

@router.post("/test-email")
async def sendTestEmail(data: TestEmailData, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.sendTestEmail(data.email)

