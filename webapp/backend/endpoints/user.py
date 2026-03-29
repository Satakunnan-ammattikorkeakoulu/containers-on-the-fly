from fastapi import APIRouter, Depends
from helpers.server import api_response, force_authentication
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from endpoints.responses import user as functionality
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")

router = APIRouter(
    prefix="/api/user",
    tags=["User"],
    responses={404: {"description": "Not found"}},
)

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
  return functionality.login(form_data.username, form_data.password)

@router.get("/check_token")
async def check_token(token: str = Depends(oauth2_scheme)):
  return functionality.check_user_token(token)

@router.post("/create_password")
async def create_password(password: str, token: str = Depends(oauth2_scheme)):
  force_authentication(token)
  return functionality.create_password(password)

@router.get("/profile")
async def profile(token: str = Depends(oauth2_scheme)):
  force_authentication(token)
  return functionality.profile(token)

@router.get("/has_password")
async def has_password(token: str = Depends(oauth2_scheme)):
  force_authentication(token)
  return functionality.has_password(token)

class ChangePasswordRequest(BaseModel):
  currentPassword: str
  newPassword: str

@router.post("/change_password")
async def change_password(request: ChangePasswordRequest, token: str = Depends(oauth2_scheme)):
  force_authentication(token)
  return functionality.change_password(token, request.currentPassword, request.newPassword)