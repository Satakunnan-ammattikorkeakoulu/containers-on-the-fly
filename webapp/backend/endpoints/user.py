"""User API endpoints for authentication, profile management, and SSH key storage.

Handles login, token validation, password management, user profile retrieval,
and SSH public key updates.
"""

from fastapi import APIRouter, Depends
from helpers.server import api_response, force_authentication
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from endpoints.responses import user as functionality
from pydantic import BaseModel
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")

router = APIRouter(
    prefix="/api/user",
    tags=["User"],
    responses={404: {"description": "Not found"}},
)

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
  """Authenticate a user with username and password.

  Args:
      form_data: OAuth2 form containing ``username`` and ``password``.

  Returns:
      API response with an access token on success, or an error message
      on failure.
  """
  return functionality.login(form_data.username, form_data.password)

@router.get("/check_token")
async def check_token(token: str = Depends(oauth2_scheme)):
  """Validate whether the provided bearer token is still active.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      API response indicating token validity and user info.
  """
  return functionality.check_user_token(token)

@router.post("/create_password")
async def create_password(password: str, token: str = Depends(oauth2_scheme)):
  """Set an initial local password for an LDAP-authenticated user.

  Args:
      password: The new password to set.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  force_authentication(token)
  return functionality.create_password(password)

@router.get("/profile")
async def profile(token: str = Depends(oauth2_scheme)):
  """Retrieve the authenticated user's profile information.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      API response containing user profile data (name, email, roles, etc.).
  """
  force_authentication(token)
  return functionality.profile(token)

@router.get("/has_password")
async def has_password(token: str = Depends(oauth2_scheme)):
  """Check whether the authenticated user has a local password set.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      API response with a boolean indicating password existence.
  """
  force_authentication(token)
  return functionality.has_password(token)

class ChangePasswordRequest(BaseModel):
  """Request body for the change-password endpoint."""

  currentPassword: str
  newPassword: str

@router.post("/change_password")
async def change_password(request: ChangePasswordRequest, token: str = Depends(oauth2_scheme)):
  """Change the authenticated user's password.

  Args:
      request: Pydantic model with ``currentPassword`` and ``newPassword``.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  force_authentication(token)
  return functionality.change_password(token, request.currentPassword, request.newPassword)

class UpdateSshKeyRequest(BaseModel):
  """Request body for updating the user's SSH public key."""

  sshPublicKey: Optional[str] = None

@router.post("/update_ssh_key")
async def update_ssh_key(request: UpdateSshKeyRequest, token: str = Depends(oauth2_scheme)):
  """Store or clear the authenticated user's SSH public key.

  The key is deployed to containers on launch so the user can SSH in
  without a password.

  Args:
      request: Pydantic model with an optional ``sshPublicKey`` string.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  force_authentication(token)
  return functionality.update_ssh_key(token, request.sshPublicKey)

class UpdateNameRequest(BaseModel):
  """Request body for updating the user's display name."""

  name: Optional[str] = None

@router.post("/update_name")
async def update_name(request: UpdateNameRequest, token: str = Depends(oauth2_scheme)):
  """Update or remove the authenticated user's display name.

  Args:
      request: Pydantic model with an optional ``name`` string.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  force_authentication(token)
  return functionality.update_name(token, request.name)

class UpdateScriptPathsRequest(BaseModel):
  """Request body for updating the user's container lifecycle script paths."""

  startScriptPath: Optional[str] = None
  stopScriptPath: Optional[str] = None

@router.post("/update_script_paths")
async def update_script_paths(request: UpdateScriptPathsRequest, token: str = Depends(oauth2_scheme)):
  """Store or clear the authenticated user's container start/stop script paths.

  These paths point to scripts inside the container that run automatically
  when containers start or stop. Per-reservation overrides can be set
  during reservation creation.

  Args:
      request: Pydantic model with optional ``startScriptPath`` and
          ``stopScriptPath`` strings.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  force_authentication(token)
  return functionality.update_script_paths(token, request.startScriptPath, request.stopScriptPath)
