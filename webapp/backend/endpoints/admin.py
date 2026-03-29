from fastapi import APIRouter, Depends, Request
from helpers.server import force_authentication, api_response
from fastapi.security import OAuth2PasswordBearer
from endpoints.responses import admin as functionality
from endpoints.models.admin import ContainerEdit, ComputerEdit, UserEdit, RoleMountsEdit, RoleHardwareLimitsEdit, RoleReservationLimitsEdit
from endpoints.models.reservation import ReservationFilters
from database import Session, Computer, ContainerPort, User, Reservation, Container, ReservedContainer, ReservedHardwareSpec, HardwareSpec, UserRole, ServerStatus, ServerLogs
from sqlalchemy import desc, Column, Integer, Text, Float, ForeignKey, DateTime, UniqueConstraint, Boolean, BigInteger, func
import datetime
from pydantic import BaseModel
from helpers.tables.role import get_roles, get_role_by_id, add_role as add_role_helper, edit_role as edit_role_helper, remove_role as remove_role_helper
from helpers.server import api_response, orm_to_dict
from typing import Dict, Any, List

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    responses={404: {"description": "Not found"}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")  # Make sure the tokenUrl is correct

@router.post("/reservations")
async def get_reservations(filters : ReservationFilters, token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.get_reservations(filters)

@router.get("/users")
async def get_users(token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.get_users()

@router.get("/hardware")
async def get_hardware(token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.get_hardware()

@router.get("/containers")
async def get_containers(token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.get_containers()

@router.get("/computers")
async def get_computers(token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.get_computers()

@router.get("/computer")
async def get_computer(computerId : int, token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.get_computer(computerId)

@router.post("/save_computer")
async def save_computer(computerEdit : ComputerEdit, token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.save_computer(computerEdit)

@router.post("/remove_computer")
async def remove_computer(computerId : int, token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.remove_computer(computerId)

@router.get("/container")
async def get_container(containerId : int, token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.get_container(containerId)

@router.post("/save_container")
async def save_container(containerEdit : ContainerEdit, token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.save_container(containerEdit)

@router.post("/remove_container")
async def remove_container(containerId : int, token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.remove_container(containerId)

@router.post("/edit_reservation")
async def edit_reservation(reservationId : int, endDate : str, token: str = Depends(oauth2_scheme)):
  force_authentication(token, "admin")
  return functionality.edit_reservation(reservationId, endDate)

@router.get("/user")
async def get_user(userId: int, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.get_user(userId)

@router.post("/save_user")
async def save_user(userEdit: UserEdit, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.save_user(userEdit.userId, userEdit.data)

@router.get("/roles")
async def get_roles(token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.get_all_roles()

@router.post("/save_role")
async def save_role(roleId: int = None, name: str = None, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    if roleId:
        return functionality.edit_role(roleId, name)
    else:
        return functionality.add_role(name)

@router.post("/remove_role")
async def remove_role(roleId: int, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.remove_role(roleId)

@router.get("/role_mounts")
async def get_role_mounts(roleId: int, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.get_role_mounts(roleId)

@router.post("/save_role_mounts")
async def save_role_mounts(roleMountsEdit: RoleMountsEdit, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.save_role_mounts(roleMountsEdit.roleId, roleMountsEdit.mounts)

@router.get("/role_hardware_limits")
async def get_role_hardware_limits(roleId: int, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.get_role_hardware_limits(roleId)

@router.post("/save_role_hardware_limits")
async def save_role_hardware_limits(roleHardwareLimitsEdit: RoleHardwareLimitsEdit, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.save_role_hardware_limits(roleHardwareLimitsEdit.roleId, roleHardwareLimitsEdit.hardwareLimits)

@router.get("/role_reservation_limits")
async def get_role_reservation_limits(roleId: int, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.get_role_reservation_limits(roleId)

@router.post("/save_role_reservation_limits")
async def save_role_reservation_limits(roleReservationLimitsEdit: RoleReservationLimitsEdit, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.save_role_reservation_limits(roleReservationLimitsEdit.roleId, roleReservationLimitsEdit.reservationLimits)

@router.get("/server/{computer_id}/monitoring")
async def get_server_monitoring(computer_id: int, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.get_server_monitoring(computer_id)

@router.get("/servers")
async def get_servers_for_monitoring(token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.get_servers_for_monitoring()

# General admin settings endpoints
class GeneralSettingsData(BaseModel):
    section: str
    settings: Dict[str, Any]

class TestEmailData(BaseModel):
    email: str

@router.get("/general-settings")
async def get_general_settings(token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.get_general_settings()

@router.post("/general-settings")
async def save_general_settings(data: GeneralSettingsData, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.save_general_settings(data.section, data.settings)

@router.post("/test-email")
async def send_test_email(data: TestEmailData, token: str = Depends(oauth2_scheme)):
    force_authentication(token, "admin")
    return functionality.send_test_email(data.email)

