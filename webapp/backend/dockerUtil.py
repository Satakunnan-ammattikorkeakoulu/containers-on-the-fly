from docker.dockerUtils import stopOrphanDockerContainer, getRunningReservedDockerContainers, getComputerId, getContainerInformation, getRunningReservations, getReservationsRequiringStart, getReservationsRequiringStop, stopDockerContainer, startDockerContainer, getReservationsRequiringRestart, restartDockerContainer
from time import sleep
from settings_handler import settings_handler
import datetime
from datetime import timezone, datetime, timedelta
import sys
from os import linesep
import psutil
import subprocess
import time
from database import ServerStatus, ServerLogs, Computer, Session

# Runs the script forever
run : bool = True
# The ID of the computer from the database which this script should react to is saved here
computerId : int = None

def timeNow():
  return datetime.now(timezone.utc)

def readVersionFile():
    """Read version information from .version file"""
    try:
        import os
        # Look for .version file in project root (3 levels up from this script)
        version_file_path = os.path.join(os.path.dirname(__file__), '..', '..', '.version')
        
        if os.path.exists(version_file_path):
            with open(version_file_path, 'r') as f:
                content = f.read().strip()
                
            # Parse the version file content
            version_info = {}
            for line in content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    version_info[key.strip()] = value.strip()
            
            return version_info.get('version'), version_info.get('updated')
        else:
            return None, None
    except Exception as e:
        print(f"Error reading version file: {e}")
        return None, None

def updateServerMonitoring():
    """Update server monitoring data in database"""
    try:
        with Session() as session:
            computer = session.query(Computer).filter(
                Computer.name == settings_handler.getSetting("docker.serverName")
            ).first()
            
            if not computer:
                print(f"Warning: Computer '{settings_handler.getSetting('docker.serverName')}' not found in database")
                return
            
            # Get or create status record
            status = session.query(ServerStatus).filter(
                ServerStatus.computerId == computer.computerId
            ).first()
            
            if not status:
                status = ServerStatus(computerId=computer.computerId)
                session.add(status)
            
            # Collect system metrics
            status.isOnline = True
            status.cpuUsagePercent = round(psutil.cpu_percent(interval=1), 1)
            status.cpuCores = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            status.memoryTotalBytes = memory.total
            status.memoryUsedBytes = memory.used
            status.memoryUsagePercent = round(memory.percent, 1)
            
            # Root disk usage (/)
            try:
                disk = psutil.disk_usage('/')
                status.diskTotalBytes = disk.total
                status.diskUsedBytes = disk.used
                status.diskFreeBytes = disk.free
                status.diskUsagePercent = round((disk.used / disk.total) * 100, 1)
            except:
                pass  # Skip if can't access root disk
            
            # Docker status
            try:
                from python_on_whales import docker
                running_containers = docker.container.list()
                all_containers = docker.container.list(all=True)
                status.dockerContainersRunning = len(running_containers)
                status.dockerContainersTotal = len(all_containers)
            except:
                status.dockerContainersRunning = None
                status.dockerContainersTotal = None
            
            # System load
            try:
                load_avg = psutil.getloadavg()
                status.loadAvg1Min = round(load_avg[0], 2)
                status.loadAvg5Min = round(load_avg[1], 2)
                status.loadAvg15Min = round(load_avg[2], 2)
            except:
                pass  # getloadavg not available on all systems
            
            # System uptime
            try:
                status.systemUptimeSeconds = int(time.time() - psutil.boot_time())
            except:
                pass
            
            # Update software version information
            try:
                version, updated_str = readVersionFile()
                if version:
                    status.softwareVersion = version
                    
                    # Parse the updated timestamp if provided
                    if updated_str:
                        try:
                            # Parse UTC timestamp format: "2025-07-21 15:12:10 UTC"
                            updated_str = updated_str.replace(' UTC', '')
                            updated_dt = datetime.strptime(updated_str, '%Y-%m-%d %H:%M:%S')
                            status.versionUpdatedAt = updated_dt.replace(tzinfo=timezone.utc)
                        except:
                            pass
            except Exception as e:
                print(f"Error updating version info: {e}")
            
            session.commit()
            
            # Update logs
            updateServerLogs(computer.computerId, session)
            
    except Exception as e:
        print(f"Error updating server monitoring: {e}")

def updateServerLogs(computer_id: int, session):
    """Update server logs in database"""
    try:
        # Backend logs
        try:
            backend_logs = subprocess.check_output(
                ["pm2", "logs", "backend", "--lines", "300", "--nostream"], 
                text=True, stderr=subprocess.STDOUT, timeout=10
            )
            updateLogRecord(session, computer_id, "backend", backend_logs, 300)
        except:
            pass
        
        # Frontend logs  
        try:
            frontend_logs = subprocess.check_output(
                ["pm2", "logs", "frontend", "--lines", "300", "--nostream"],
                text=True, stderr=subprocess.STDOUT, timeout=10
            )
            updateLogRecord(session, computer_id, "frontend", frontend_logs, 300)
        except:
            pass
        
        # Docker utility logs
        try:
            docker_logs = subprocess.check_output(
                ["pm2", "logs", "backendDockerUtil", "--lines", "300", "--nostream"],
                text=True, stderr=subprocess.STDOUT, timeout=10
            )
            updateLogRecord(session, computer_id, "docker_utility", docker_logs, 300)
        except:
            pass
            
    except Exception as e:
        print(f"Error updating server logs: {e}")

def updateLogRecord(session, computer_id: int, log_type: str, content: str, lines: int):
    """Helper function to upsert log records"""
    try:
        log_record = session.query(ServerLogs).filter(
            ServerLogs.computerId == computer_id,
            ServerLogs.logType == log_type
        ).first()
        
        if not log_record:
            log_record = ServerLogs(
                computerId=computer_id,
                logType=log_type
            )
            session.add(log_record)
        
        log_record.logContent = content
        log_record.logLines = lines
        session.commit()
        
    except Exception as e:
        print(f"Error updating {log_type} logs: {e}")

def main():
  while (run):
    for i in range(6):
      stopFinishedServers()
      startNewServers()
      restartCrashedServers()
      restartServersRequiringRestart()
      
      # Update monitoring data every 3rd iteration (every 30 seconds)
      if i % 3 == 0:
        updateServerMonitoring()
      
      sleep(10)
    # Run this larger cleanup below every 60 seconds (1 minute)
    stopOrphanContainerReservations()
    

def stopOrphanContainerReservations():
  '''
  Gathers a list of orphan (not bound to started server) reservations and stops & removes them.
  Basically, we verify for each container running in Docker that the reservation is also marked as started in database.
  Every reservation which is not started in the database will be stopped and removed.
  These orphan containers can occur when the script errors out, for ex, and the server was never removed.
  '''

  try:
    # Get all containers marked as started in the database
    reservations = getRunningReservations(computerId)
    for reservation in reservations:
      print(reservation.reservedContainer.containerDockerId)
    
    # Get all Docker container reservations (container name starting with "reservation-"") really running on this computer
    docker_reservation_containers = getRunningReservedDockerContainers()
    for container in docker_reservation_containers:
      time_running = datetime.now(timezone.utc) - container.state.started_at
      # If the container has been running for over 30 minutes, check that it is really marked as running in the database
      if time_running > timedelta(minutes=30):
        is_running = False
        for reservation in reservations:
          if reservation.reservedContainer.containerDockerName == container.name: is_running = True
        if is_running:
          pass
        else:
          print("Container Docker reservation not synchronized with database! Reservation ID: " + str(reservation.reservationId) + " and container name: " + container.name)
          stopOrphanDockerContainer(container.name)
  except Exception as e:
    print("Error stopping (cleaning up) orphan containers:")
    print(e)

def stopFinishedServers():
  '''
  Gathers a list of reservations (containers) which reservation is due, status is "started"
  and stops them one by one.
  '''
  global computerId
  reservations = getReservationsRequiringStop(computerId)
  for reservation in reservations:
    if settings_handler.getSetting("docker.enabled") == True:
      print(timeNow(), ": Stopping Docker server for reservation with reservationId: ",  reservation.reservationId)
      stopDockerContainer(reservation.reservationId)

def startNewServers():
  '''
  Gathers a list of reservations (containers) requiring to be started in the current computer (state is 'reserved')
  and starts them one by one.
  '''
  global computerId
  reservations = getReservationsRequiringStart(computerId)
  for reservation in reservations:
    if settings_handler.getSetting("docker.enabled") == True:
      print(timeNow(), ": Starting Docker server for reservation with reservationId: ",  reservation.reservationId)
      startDockerContainer(reservation.reservationId)

def restartCrashedServers():
  '''
  Gathers a list of crashed reservations (containers) requiring to be restarted in the current computer (state is 'error')
  and starts them one by one.
  '''
  global computerId
  reservations = getRunningReservations(computerId)
  for reservation in reservations:
    if settings_handler.getSetting("docker.enabled") == True:
      try:
        containerName, containerState = getContainerInformation(reservation.reservationId)
        #print(containerName, containerState)
        #print(containerState.state.status)
        if containerState.state.status == "exited":
          restartDockerContainer(reservation.reservationId)
      except Exception as e:
        print(f"Error restarting a crashed container:")
        print(e)
        pass
      
      #print(timeNow(), ": Restarting Docker server for reservation with reservationId: ",  reservation.reservationId)
      #startDockerContainer(reservation.reservationId)

def restartServersRequiringRestart():
  '''
  Gathers a list of reservations (containers) requiring to be restarted in the current computer (state is 'restart')
  and starts them one by one.
  '''
  global computerId
  reservations = getReservationsRequiringRestart(computerId)

  for reservation in reservations:
    if settings_handler.getSetting("docker.enabled") == True:
      try:
        restartDockerContainer(reservation.reservationId)
      except Exception as e:
        print(f"Error restarting a container:")
        print(e)
        pass
      
      #print(timeNow(), ": Restarting Docker server for reservation with reservationId: ",  reservation.reservationId)
      #startDockerContainer(reservation.reservationId)

if __name__ == "__main__":
  print("AI Server Docker utility started.")
  print("This software will run infinitely and start / stop servers for reservations." + linesep)

  # Check that docker support has been enabled
  if (settings_handler.getSetting("docker.enabled") != True):
    print("!!! Docker support has not been enabled, so this script does nothing. Enable it with settings.json setting docker.enabled: true !!!" + linesep)

  # Get ID of the computer from the database based on the settings.json key docker.serverName.
  # Exit on any errors
  serverName = settings_handler.getSetting("docker.serverName")
  if not serverName:
    print("!!! You need to specify the name of the server in settings.json file, in key docker.serverName. The name should be exactly the same as in database !!! Exiting." + linesep)
    sys.exit()
  computerId = getComputerId(serverName)
  if not computerId:
    print("!!! Could not find computer with this name from the database. settings.json should contain docker.serverName and the name should be exactly the same as the computer in the database. !!! Exiting." + linesep)
    sys.exit()

  main()