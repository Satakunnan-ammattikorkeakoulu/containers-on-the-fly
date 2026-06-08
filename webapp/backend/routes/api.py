"""API router configuration and application startup initialization.

Registers all endpoint routers (user, reservation, admin, app) onto a
single FastAPI APIRouter. Also runs one-time startup logic when the module
is imported: ensures required roles exist ("everyone", "admin").
"""

from fastapi import APIRouter
from endpoints import user, reservation, admin, app, daemon, legal
from helpers.settings_handler import settings_handler
from helpers.logger import log
from database import Session, Role
from sqlalchemy import select

router = APIRouter()
router.include_router(user.router)
router.include_router(reservation.router)
router.include_router(admin.router)
router.include_router(app.router)
router.include_router(daemon.router)
router.include_router(legal.router)


# Run code here when server starts

if settings_handler.get_setting("app.production") == True:
  log.info("Running server in production mode")
else:
  log.info("Running server in development mode")

# Add everyone role if it does not exist
with Session() as session:
  everyoneRole = session.execute(select(Role).where(Role.name == "everyone")).scalar_one_or_none()
  if everyoneRole is None:
    log.info("Creating role 'everyone'")
    session.add(Role(
      name = "everyone"
    ))
    session.commit()

# Add admin role if it does not exist
with Session() as session:
  adminRole = session.execute(select(Role).where(Role.name == "admin")).scalar_one_or_none()
  if adminRole is None:
    log.info("Creating role 'admin'")
    session.add(Role(
      name = "admin"
    ))
    session.commit()

