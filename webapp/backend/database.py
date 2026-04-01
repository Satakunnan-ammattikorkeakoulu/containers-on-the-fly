"""SQLAlchemy ORM models and database engine configuration.

Defines all database tables as SQLAlchemy ORM classes and creates the
shared engine and session factory used throughout the application.
Uses MariaDB via PyMySQL with connection pooling.
"""

from sqlalchemy import create_engine
from settings_handler import settings_handler
import pymysql
engine = create_engine(
    settings_handler.get_setting("database.engineUri"), 
    echo=settings_handler.get_setting("database.debugPrinting"), 
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    pool_pre_ping=True      # Test connections before using them
)
from sqlalchemy.orm import declarative_base
Base = declarative_base()

from sqlalchemy import Column, Integer, Text, Float, ForeignKey, DateTime, UniqueConstraint, Boolean, BigInteger
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class User(Base):
  """Application user account.

  Stores credentials, authentication tokens, and SSH keys.
  Users can have multiple roles and reservations.
  """
  __tablename__ = "User"

  userId = Column(Integer, primary_key = True, autoincrement = True)
  email = Column(Text, nullable = False)
  password = Column(Text, nullable = True)
  passwordSalt = Column(Text, nullable = True)
  loginToken = Column(Text, nullable = True)
  loginTokenCreatedAt = Column(DateTime, nullable = True)
  userCreatedAt = Column(DateTime(timezone=True), server_default=func.now())
  userUpdatedAt = Column(DateTime(timezone=True), onupdate=func.now())
  sshPublicKey = Column(Text, nullable = True)

  roles = relationship("Role", secondary = "UserRole", back_populates = "users", single_parent=True)
  reservations = relationship("Reservation", back_populates = "user")

class UserWhitelist(Base):
  """Email whitelist entry for access control.

  When whitelisting is enabled, only email addresses present in this table
  are allowed to log in.
  """
  __tablename__ = "UserWhitelist"

  userWhitelistId = Column(Integer, primary_key = True, autoincrement = True)
  email = Column(Text, nullable = True, unique = True)

class Role(Base):
  """User role for access control and resource limits.

  Roles group users together and define per-role hardware limits,
  mount points, and reservation constraints.
  """
  __tablename__ = "Role"

  roleId = Column(Integer, primary_key = True, autoincrement = True)
  name = Column(Text, nullable = False, unique = True)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

  users = relationship("User", secondary = "UserRole", back_populates = "roles", single_parent=True)
  mounts = relationship("RoleMount", back_populates="role")
  hardwareLimits = relationship("RoleHardwareLimit", back_populates="role")
  reservationLimits = relationship("RoleReservationLimit", back_populates="role", uselist=False)

class UserRole(Base):
  """Many-to-many association between users and roles."""
  __tablename__ = "UserRole"

  userRoleId = Column(Integer, primary_key = True, autoincrement = True)
  userId = Column(ForeignKey("User.userId"), nullable = False)
  roleId = Column(ForeignKey("Role.roleId"), nullable = False)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

class Container(Base):
  """Docker container image definition available for reservation.

  Represents a reservable container type with its Docker image name,
  display name, and associated service ports.
  """
  __tablename__ = "Container"

  containerId = Column(Integer, primary_key = True, autoincrement = True)
  public = Column(Boolean, nullable = False)
  imageName = Column(Text, unique = True, nullable = False)
  name = Column(Text, nullable = False)
  removed = Column(Boolean, nullable = True)
  description = Column(Text, nullable = True)
  dockerfileCommands = Column(Text, nullable = True)
  baseImage = Column(Text, nullable = True)
  buildStatus = Column(Text, nullable = True)  # null | pending | building | success | failed
  buildLog = Column(LONGTEXT, nullable = True)
  containerUsername = Column(Text, nullable = True)  # default "user"
  passwordCommand = Column(Text, nullable = True)  # template with {username}, {password}
  sshKeyDeployCommands = Column(Text, nullable = True)  # template with {username}, {ssh_key}
  containerCmd = Column(Text, nullable = True)  # CMD instruction, default: ["/bin/bash","-c", "/usr/sbin/sshd -D ;"]
  managedExternally = Column(Boolean, nullable = True)  # True = pre-built image, False = Image Builder, null = legacy (treated as True)
  imageSize = Column(BigInteger, nullable = True)  # Image size in bytes, updated by daemon after build or on startup
  lastBuiltAt = Column(DateTime(timezone=True), nullable = True)  # When the image was last successfully built
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

  reservedContainers = relationship("ReservedContainer", back_populates = "container")
  containerPorts = relationship("ContainerPort", back_populates = "container")

class ContainerPort(Base):
  """Service port definition for a container image.

  Maps a service name (e.g. SSH, HTTP) to an internal container port.
  When a container is reserved, each ContainerPort gets an assigned
  external port via ReservedContainerPort.
  """
  __tablename__ = "ContainerPort"

  containerPortId = Column(Integer, primary_key = True, autoincrement = True)
  containerId = Column(ForeignKey("Container.containerId"), nullable = False)
  serviceName = Column(Text, nullable = False)
  port = Column(Integer, nullable = False)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

  container = relationship("Container", back_populates = "containerPorts")
  reservedContainerPorts = relationship("ReservedContainerPort", back_populates = "containerPort")

class ReservedContainer(Base):
  """Instance of a running or scheduled Docker container.

  Created when a user makes a reservation. Tracks the Docker container
  lifecycle including container ID, status, SSH credentials, and
  memory configuration (shared memory and RAM disk percentages).
  """
  __tablename__ = "ReservedContainer"

  reservedContainerId = Column(Integer, primary_key = True, autoincrement = True)
  containerId = Column(ForeignKey("Container.containerId"), nullable = False)
  startedAt = Column(DateTime, nullable = True)
  stoppedAt = Column(DateTime, nullable = True)
  containerDockerName = Column(Text, nullable = True)
  containerStatus = Column(Text, nullable = True) # Coming from Docker
  containerDockerId = Column(Text, nullable = True) # Coming from Docker
  containerId = Column(ForeignKey("Container.containerId"), nullable = False)
  sshPassword = Column(Text, nullable = True)
  containerDockerErrorMessage = Column(Text, nullable = True)
  shmSizePercent = Column(Integer, nullable = False, default=50) # Shared memory size as percentage of RAM (0-90)
  ramDiskSizePercent = Column(Integer, nullable = False, default=0) # RAM disk size as percentage of RAM (0-60)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

  reservation = relationship("Reservation", back_populates = "reservedContainer")
  container = relationship("Container", back_populates = "reservedContainers")
  reservedContainerPorts = relationship("ReservedContainerPort", back_populates = "reservedContainer")

class ReservedContainerPort(Base):
  """Port mapping for a reserved container instance.

  Maps a container's internal service port (ContainerPort) to an
  externally accessible port on the host machine.
  """
  __tablename__ = "ReservedContainerPort"

  reservedContainerPortId = Column(Integer, primary_key = True, autoincrement = True)
  reservedContainerId = Column(ForeignKey("ReservedContainer.reservedContainerId"), nullable = False)
  containerPortForeign = Column(ForeignKey("ContainerPort.containerPortId"), nullable = False)
  outsidePort = Column(Integer, nullable = False)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
  UniqueConstraint('reservedContainerId', 'localPort', name='outsidePort')

  reservedContainer = relationship("ReservedContainer", back_populates = "reservedContainerPorts")
  containerPort = relationship("ContainerPort", back_populates = "reservedContainerPorts")

class Reservation(Base):
  """Container reservation linking a user, container, computer, and time slot.

  Tracks the full lifecycle of a reservation through statuses:
  reserved, started, stopped, error, restart.
  """
  __tablename__ = "Reservation"

  reservationId = Column(Integer, primary_key = True, autoincrement = True)
  reservedContainerId = Column(ForeignKey("ReservedContainer.reservedContainerId"), nullable = False)
  computerId = Column(ForeignKey("Computer.computerId"), nullable = False)
  userId = Column(ForeignKey("User.userId"), nullable = False)
  startDate = Column(DateTime, nullable = False)
  endDate = Column(DateTime, nullable = False)
  description = Column(Text, nullable = True)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
  status = Column(Text, nullable = False) # reserved, started, stopped, error, restart

  user = relationship("User", back_populates = "reservations")
  reservedContainer = relationship("ReservedContainer", back_populates = "reservation")
  reservedHardwareSpecs = relationship("ReservedHardwareSpec", back_populates = "reservation")
  computer = relationship("Computer", back_populates = "reservations")

class Computer(Base):
  """Container server (physical or virtual machine) that hosts Docker containers.

  Each computer has its own hardware specs, IP address, and can be
  marked public or removed. Supports server status monitoring.
  """
  __tablename__ = "Computer"

  computerId = Column(Integer, primary_key = True, autoincrement = True)
  public = Column(Boolean, nullable = False)
  name = Column(Text, nullable = False, unique = True)
  removed = Column(Boolean, nullable = True)
  ip = Column(Text, nullable = False)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

  hardwareSpecs = relationship("HardwareSpec", back_populates = "computer")
  reservations = relationship("Reservation", back_populates = "computer")
  roleMounts = relationship("RoleMount", back_populates="computer")
  status = relationship("ServerStatus", back_populates="computer", uselist=False)

class HardwareSpec(Base):
  """Hardware resource specification for a computer (e.g. GPU, RAM, CPU cores).

  Defines the resource type, total available amount, and per-user
  limits. Each spec can have role-based overrides via RoleHardwareLimit.
  """
  __tablename__ = "HardwareSpec"

  hardwareSpecId = Column(Integer, primary_key = True, autoincrement = True)
  computerId = Column(ForeignKey("Computer.computerId"), nullable = False)
  internalId = Column(Text, nullable = True)
  type = Column(Text, nullable = False)
  maximumAmount = Column(Float, nullable = False)
  minimumAmount = Column(Float, nullable = False)
  maximumAmountForUser = Column(Float, nullable = False)
  defaultAmountForUser = Column(Float, nullable = False)
  format = Column(Text, nullable = False)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

  computer = relationship("Computer", back_populates = "hardwareSpecs")
  reservations = relationship("ReservedHardwareSpec", back_populates = "hardwareSpec")
  roleLimits = relationship("RoleHardwareLimit", back_populates="hardwareSpec")

class ReservedHardwareSpec(Base):
  """Hardware resource allocation for a specific reservation.

  Records the amount of each hardware resource allocated to a
  reservation (e.g. 2 GPUs, 16 GB RAM).
  """
  __tablename__ = "ReservedHardwareSpec"

  reservedHardwareSpecId = Column(Integer, primary_key = True, autoincrement = True)
  reservationId = Column(ForeignKey("Reservation.reservationId"), nullable = False)
  hardwareSpecId = Column(ForeignKey("HardwareSpec.hardwareSpecId"), nullable = False)
  amount = Column(Float, nullable = False)
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

  hardwareSpec = relationship("HardwareSpec", back_populates = "reservations")
  reservation = relationship("Reservation", back_populates = "reservedHardwareSpecs")

class RoleMount(Base):
    """Host-to-container volume mount assigned to a role on a specific computer.

    Allows administrators to configure persistent storage mounts that are
    automatically attached to containers reserved by users with this role.
    """
    __tablename__ = "RoleMount"

    roleMountId = Column(Integer, primary_key=True, autoincrement=True)
    roleId = Column(ForeignKey("Role.roleId"), nullable=False)
    computerId = Column(ForeignKey("Computer.computerId"), nullable=False)
    hostPath = Column(Text, nullable=False)
    containerPath = Column(Text, nullable=False)
    readOnly = Column(Boolean, nullable=False)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    role = relationship("Role", back_populates="mounts")
    computer = relationship("Computer", back_populates="roleMounts")

class RoleHardwareLimit(Base):
    """Per-role override for hardware resource limits.

    Allows setting a maximum hardware allocation for a specific role on
    a specific hardware spec, overriding the default maximumAmountForUser.
    """
    __tablename__ = "RoleHardwareLimit"

    roleHardwareLimitId = Column(Integer, primary_key=True, autoincrement=True)
    roleId = Column(ForeignKey("Role.roleId", name="fk_RoleHardwareLimit_roleId", ondelete="CASCADE"), nullable=False, index=True)
    hardwareSpecId = Column(ForeignKey("HardwareSpec.hardwareSpecId", name="fk_RoleHardwareLimit_hardwareSpecId", ondelete="CASCADE"), nullable=False, index=True)
    maximumAmountForRole = Column(Integer, nullable=True)
    createdAt = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('roleId', 'hardwareSpecId', name='unique_role_hardware'),
    )
    
    role = relationship("Role", back_populates="hardwareLimits")
    hardwareSpec = relationship("HardwareSpec", back_populates="roleLimits")

class RoleReservationLimit(Base):
    """Per-role reservation duration and concurrency limits.

    Overrides default reservation constraints (min/max duration, max
    active reservations) for users belonging to this role.
    NULL values fall back to system defaults.
    """
    __tablename__ = "RoleReservationLimit"

    roleReservationLimitId = Column(Integer, primary_key=True, autoincrement=True)
    roleId = Column(ForeignKey("Role.roleId"), nullable=False)
    minDuration = Column(Integer, nullable=True)  # hours (NULL = use default)
    maxDuration = Column(Integer, nullable=True)  # hours (NULL = use default)
    maxActiveReservations = Column(Integer, nullable=True)  # count (NULL = use default)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('roleId', name='unique_role'),
    )
    
    role = relationship("Role", back_populates="reservationLimits")

class ServerStatus(Base):
    """Real-time health and performance metrics for a container server.

    Stores CPU, memory, disk, Docker, and system load metrics collected
    by the monitoring daemon. One row per computer (1:1 with Computer).
    """
    __tablename__ = "ServerStatus"

    computerId = Column(ForeignKey("Computer.computerId"), primary_key=True)

    # Basic Health
    isOnline = Column(Boolean, nullable=False, default=False)
    
    # CPU Metrics
    cpuUsagePercent = Column(Float, nullable=True)
    cpuCores = Column(Integer, nullable=True)
    
    # Memory Metrics  
    memoryTotalBytes = Column(BigInteger, nullable=True)
    memoryUsedBytes = Column(BigInteger, nullable=True)
    memoryUsagePercent = Column(Float, nullable=True)
    
    # Root Disk Usage (/)
    diskTotalBytes = Column(BigInteger, nullable=True)
    diskUsedBytes = Column(BigInteger, nullable=True)
    diskFreeBytes = Column(BigInteger, nullable=True)
    diskUsagePercent = Column(Float, nullable=True)
    
    # Docker Status
    dockerContainersRunning = Column(Integer, nullable=True)
    dockerContainersTotal = Column(Integer, nullable=True)
    
    # System Load
    loadAvg1Min = Column(Float, nullable=True)
    loadAvg5Min = Column(Float, nullable=True)
    loadAvg15Min = Column(Float, nullable=True)
    
    # Uptime (in seconds)
    systemUptimeSeconds = Column(BigInteger, nullable=True)
    
    # Software version info
    softwareVersion = Column(Text, nullable=True)
    versionUpdatedAt = Column(DateTime(timezone=True), nullable=True)
    
    # Last update timestamp
    lastUpdatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    computer = relationship("Computer", back_populates="status")

class ServerLogs(Base):
    """Cached log output from a container server's services.

    Stores the last N lines of backend, frontend, or docker_utility logs
    per computer. Unique per (computerId, logType) pair.
    """
    __tablename__ = "ServerLogs"

    serverLogId = Column(Integer, primary_key=True, autoincrement=True)
    computerId = Column(ForeignKey("Computer.computerId"), nullable=False)
    logType = Column(Text, nullable=False)  # 'backend', 'frontend', 'docker_utility'
    
    logContent = Column(LONGTEXT, nullable=True)  # Store last N lines
    logLines = Column(Integer, nullable=True)  # How many lines stored
    
    lastUpdatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Unique constraint for upsert per computer+logtype
    __table_args__ = (UniqueConstraint('computerId', 'logType', name='unique_computer_logtype'),)
    
    computer = relationship("Computer")

class UserBlacklist(Base):
  """Email blacklist entry for access control.

  When blacklisting is enabled, email addresses in this table are
  denied login access.
  """
  __tablename__ = "UserBlacklist"

  userBlacklistId = Column(Integer, primary_key = True, autoincrement = True)
  email = Column(Text, nullable = True, unique = True)

class SystemSetting(Base):
  """Runtime-configurable application setting stored in the database.

  Settings are keyed by settingKey (e.g. 'general.applicationName') and
  store values as strings with a dataType indicator for parsing.
  Managed via the admin interface and accessed through settings_handler.
  """
  __tablename__ = "SystemSetting"

  systemSettingId = Column(Integer, primary_key = True, autoincrement = True)
  settingKey = Column(Text, nullable = False, unique = True)
  settingValue = Column(Text, nullable = True)  # Store as JSON for complex values
  dataType = Column(Text, nullable = False)  # 'boolean', 'integer', 'text', 'email', 'json'
  description = Column(Text, nullable = True)  # Optional description of what this setting does
  createdAt = Column(DateTime(timezone=True), server_default=func.now())
  updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

# Create session to interact with the database
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind = engine)

# DEBUG: DEBUG THE AMOUNT OF POOLED AND OVERFLOW CONNECTIONS
'''from sqlalchemy import event
def checkout_listener(dbapi_con, con_record, con_proxy):
    print("A connection was checked out")
def checkin_listener(dbapi_con, con_record):
    print("A connection was returned to the pool")
    with Session() as session:
      print(session.get_bind().pool.status())
event.listen(engine, "checkout", checkout_listener)
event.listen(engine, "checkin", checkin_listener)'''