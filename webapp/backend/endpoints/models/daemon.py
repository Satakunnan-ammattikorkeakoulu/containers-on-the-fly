"""Pydantic request and response models for daemon API endpoints.

Defines the data structures used by the container server daemon to
report container lifecycle events, build progress, and server monitoring
data back to the backend.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# --- Action request models (daemon reports outcomes) ---

class PortMapping(BaseModel):
    """A single port mapping created when a container starts."""
    containerPortId: int
    outsidePort: int


class ReservationStartedRequest(BaseModel):
    """Reported by daemon when a container starts successfully."""
    containerDockerName: str
    sshPassword: str
    containerDockerId: str
    ports: List[PortMapping]
    nonCriticalErrors: str = ""


class ReservationStartFailedRequest(BaseModel):
    """Reported by daemon when a container fails to start."""
    errorMessage: str


class ReservationRestartedRequest(BaseModel):
    """Reported by daemon after a container restart attempt."""
    success: bool
    errorMessage: str = ""


class ReservationPausedRequest(BaseModel):
    """Reported by daemon when a low-priority container is paused."""
    imageName: str
    computerName: str


# --- Build request models ---

class BuildProgressRequest(BaseModel):
    """Reported by daemon during an image build."""
    buildLog: str
    buildStatus: str = "building"


class BuildCompleteRequest(BaseModel):
    """Reported by daemon when an image build finishes."""
    buildStatus: str
    buildLog: str
    imageSize: Optional[int] = None
    lastBuiltAt: Optional[str] = None


class ImageRemovedRequest(BaseModel):
    """Reported by daemon when an image is removed."""
    buildStatus: str


class ImageSizeRequest(BaseModel):
    """Reported by daemon to update an image's size."""
    imageSize: Optional[int] = None


class ImageSizeBatchItem(BaseModel):
    """A single image size entry for batch updates."""
    imageName: str
    imageSize: Optional[int] = None


class ImageSizeBatchRequest(BaseModel):
    """Batch update image sizes on startup."""
    images: List[ImageSizeBatchItem]


# --- Monitoring request models ---

class LogEntry(BaseModel):
    """Log content for a single service."""
    content: Optional[str] = None
    lines: Optional[int] = None


class MonitoringRequest(BaseModel):
    """Server metrics and logs submitted by daemon."""
    cpuUsagePercent: Optional[float] = None
    cpuCores: Optional[int] = None
    memoryTotalBytes: Optional[int] = None
    memoryUsedBytes: Optional[int] = None
    memoryUsagePercent: Optional[float] = None
    diskTotalBytes: Optional[int] = None
    diskUsedBytes: Optional[int] = None
    diskFreeBytes: Optional[int] = None
    diskUsagePercent: Optional[float] = None
    dockerContainersRunning: Optional[int] = None
    dockerContainersTotal: Optional[int] = None
    loadAvg1Min: Optional[float] = None
    loadAvg5Min: Optional[float] = None
    loadAvg15Min: Optional[float] = None
    systemUptimeSeconds: Optional[int] = None
    softwareVersion: Optional[str] = None
    versionUpdatedAt: Optional[str] = None
    logs: Optional[Dict[str, LogEntry]] = None
