from sqlalchemy import create_engine
from settings import settings
engine = create_engine(settings.database["engineUri"] + settings.database["filePath"], echo=settings.database["debugPrinting"], future=True)
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class User(Base):
  __tablename__ = "User"
  userId = Column(Integer, primary_key = True, autoincrement = True)
  email = Column(String, nullable = False)
  password = Column(String, nullable = True)
  passwordSalt = Column(String, nullable = True)
  loginToken = Column(String, nullable = True)
  loginTokenCreatedAt = Column(DateTime, nullable = True)
  userCreatedAt = Column(DateTime(timezone=True), server_default=func.now())
  userUpdatedAt = Column(DateTime(timezone=True), onupdate=func.now())
  userStorage = relationship("UserStorage", back_populates = "user")
  roles = relationship("Role", secondary = "UserRole", back_populates = "users", single_parent=True)
  reservations = relationship("Reservation", back_populates = "user")

# If whitelisting is enabled, then only the email addresses specified here can login
class UserWhitelist(Base):
  __tablename__ = "UserWhitelist"
  userWhitelistId = Column(Integer, primary_key = True, autoincrement = True)
  email = Column(String, nullable = True, unique = True)

class UserStorage(Base):
  __tablename__ = "UserStorage"
  userStorageId = Column(Integer, primary_key = True, autoincrement = True)
  userId = Column(ForeignKey('User.userId'), unique = True, nullable = False)
  maxSpace = Column(Float, nullable = False)
  maxSpaceFormat = Column(String, nullable = False)
  UniqueConstraint('userStorageId', 'userId', name='uniqueUserStorage')
  user = relationship("User", back_populates = "userStorage")
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

class Role(Base):
  __tablename__ = "Role"
  roleId = Column(Integer, primary_key = True, autoincrement = True)
  name = Column(String, nullable = False, unique = True)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
  users = relationship("User", secondary = "UserRole", back_populates = "roles", single_parent=True)

class UserRole(Base):
  __tablename__ = "UserRole"
  userRoleId = Column(Integer, primary_key = True, autoincrement = True)
  userId = Column(ForeignKey("User.userId"), nullable = False)
  roleId = Column(ForeignKey("Role.roleId"), nullable = False)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

class Container(Base):
  __tablename__ = "Container"
  containerId = Column(Integer, primary_key = True, autoincrement = True)
  public = Column(Boolean, nullable = False)
  imageName = Column(String, unique = True, nullable = False)
  name = Column(String, nullable = False)
  description = Column(String, nullable = True)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
  reservedContainers = relationship("ReservedContainer", back_populates = "container")

class ReservedContainer(Base):
  __tablename__ = "ReservedContainer"
  reservedContainerId = Column(Integer, primary_key = True, autoincrement = True)
  containerId = Column(ForeignKey("Container.containerId"), nullable = False)
  startedAt = Column(DateTime, nullable = True)
  stoppedAt = Column(DateTime, nullable = True)
  containerStatus = Column(String, nullable = True) # Coming from Docker
  containerDockerId = Column(String, nullable = True) # Coming from Docker
  containerId = Column(ForeignKey("Container.containerId"), nullable = False)
  sshPassword = Column(String, nullable = True)
  reservation = relationship("Reservation", back_populates = "reservedContainer")
  container = relationship("Container", back_populates = "reservedContainers")
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

class Reservation(Base):
  __tablename__ = "Reservation"
  reservationId = Column(Integer, primary_key = True, autoincrement = True)
  reservedContainerId = Column(ForeignKey("ReservedContainer.reservedContainerId"), nullable = False)
  computerId = Column(ForeignKey("Computer.computerId"), nullable = False)
  userId = Column(ForeignKey("User.userId"), nullable = False)
  startDate = Column(DateTime, nullable = False)
  endDate = Column(DateTime, nullable = False)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
  status = Column(String, nullable = False) # reserved, started, stopped
  user = relationship("User", back_populates = "reservations")
  reservedContainer = relationship("ReservedContainer", back_populates = "reservation")
  reservedHardwareSpecs = relationship("ReservedHardwareSpec", back_populates = "reservation")
  computer = relationship("Computer", back_populates = "reservations")

class Computer(Base):
  __tablename__ = "Computer"
  computerId = Column(Integer, primary_key = True, autoincrement = True)
  public = Column(Boolean, nullable = False)
  name = Column(String, nullable = False, unique = True)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
  hardwareSpecs = relationship("HardwareSpec", back_populates = "computer")
  reservations = relationship("Reservation", back_populates = "computer")

class HardwareSpec(Base):
  __tablename__ = "HardwareSpec"
  hardwareSpecId = Column(Integer, primary_key = True, autoincrement = True)
  computerId = Column(ForeignKey("Computer.computerId"), nullable = False)
  type = Column(String, nullable = False)
  maximumAmount = Column(Float, nullable = False)
  minimumAmount = Column(Float, nullable = False)
  maximumAmountForUser = Column(Float, nullable = False)
  defaultAmountForUser = Column(Float, nullable = False)
  format = Column(String, nullable = False)
  computer = relationship("Computer", back_populates = "hardwareSpecs")
  reservations = relationship("ReservedHardwareSpec", back_populates = "hardwareSpec")
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

class ReservedHardwareSpec(Base):
  __tablename__ = "ReservedHardwareSpec"
  reservedHardwareSpecId = Column(Integer, primary_key = True, autoincrement = True)
  reservationId = Column(ForeignKey("Reservation.reservationId"), nullable = False)
  hardwareSpecId = Column(ForeignKey("HardwareSpec.hardwareSpecId"), nullable = False)
  amount = Column(Float, nullable = False)
  #UniqueConstraint('reservationId', 'hardwareSpecId', name='uniqueHardwareSpec')
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
  hardwareSpec = relationship("HardwareSpec", back_populates = "reservations")
  reservation = relationship("Reservation", back_populates = "reservedHardwareSpecs")

# Create the tables
Base.metadata.create_all(engine)

# Create session to interact with the database
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind = engine)
session = Session()