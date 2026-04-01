"""Docker image builder for on-the-fly container image creation.

Generates Dockerfiles from admin-provided body (or default template),
builds the image, and pushes it to the local registry.
Runs on the Docker utility side only (called from daemon.py).

Also provides default constants for runtime post-start commands
(password setting, SSH key deployment) that can be customized per container.
"""

import tempfile
import os
import re
import shutil
import traceback
from datetime import datetime, timezone
from python_on_whales import docker
from database import Session, Container
from sqlalchemy import select
from settings_handler import settings_handler

# Pattern for valid Docker image names (alphanumeric, dots, slashes, colons, hyphens, underscores)
_VALID_IMAGE_NAME_RE = re.compile(r'^[a-zA-Z0-9._/:\-]+$')

# Default CMD instruction for containers
DEFAULT_CMD = '["/bin/bash","-c", "/usr/sbin/sshd -D ;"]'

# Default password command template — executed after container start.
# Variables: {username}, {password}
DEFAULT_PASSWORD_COMMAND = "/bin/echo '{username}:{password}' | /usr/sbin/chpasswd"

# Default SSH key deployment commands template — executed after container start
# if the user has an SSH public key configured.
# Variables: {username}, {ssh_key}
DEFAULT_SSH_KEY_DEPLOY_COMMANDS = """mkdir -p /home/{username}/.ssh && chmod 700 /home/{username}/.ssh
cat <<'SSHEOF' > /home/{username}/.ssh/authorized_keys
{ssh_key}
SSHEOF
chmod 600 /home/{username}/.ssh/authorized_keys && chown -R {username}:$(id -gn {username}) /home/{username}/.ssh"""


def get_default_dockerfile_body(username="user"):
    """Get the default Dockerfile body with the given username interpolated.

    Returns the full body between FROM and CMD, including package
    installation, containerfly group creation, user creation, and SSH
    configuration. This is used as the default when creating a new
    container and as a fallback for legacy containers.

    Args:
        username: Linux username to create inside the container.

    Returns:
        str: Default Dockerfile body with username interpolated.
    """
    return f"""# Update the package list and install necessary packages
RUN apt-get update && \\
    apt-get install -y \\
    passwd \\
    sudo \\
    openssh-server \\
    zip \\
    htop \\
    screen \\
    libgl1-mesa-glx \\
    python3-pip

# Create containerfly group (GID 5620) — required for volume mount permissions.
# The GID must match the host's containerfly group for mounted files to be accessible.
RUN groupadd -g 5620 containerfly

# Create user '{username}' with containerfly as primary group
RUN useradd -rm -d /home/{username} -s /bin/bash -g containerfly -G sudo -u 1000 {username}
RUN echo '{username}:password' | chpasswd

# Configure SSH server to listen on port 22 and allow root login
RUN sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config && \\
    sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \\
    mkdir /var/run/sshd
RUN service ssh start

# Set default user working directory
USER {username}
WORKDIR /home/{username}

USER root

# Open port 22 (SSH)
EXPOSE 22"""


def generate_dockerfile(base_image, dockerfile_body, cmd=None):
    """Generate a full Dockerfile from base image, body, and CMD.

    Args:
        base_image: Docker base image (e.g. 'ubuntu:22.04').
        dockerfile_body: Full Dockerfile body between FROM and CMD.
        cmd: CMD instruction string. Defaults to DEFAULT_CMD.

    Returns:
        str: Complete Dockerfile content ready to be written to disk.
    """
    if not _VALID_IMAGE_NAME_RE.match(base_image):
        raise ValueError(f"Invalid base image name: {base_image}")

    cmd = cmd or DEFAULT_CMD
    lines = [f"FROM {base_image}"]
    lines.append("")
    lines.append(dockerfile_body.strip())
    lines.append("")
    lines.append(f"CMD {cmd}")
    lines.append("")

    return "\n".join(lines)


def build_and_push_image(container_id):
    """Build a Docker image for a container definition and push to registry.

    Reads the container's baseImage and dockerfileCommands from the database,
    generates a Dockerfile, builds the image, pushes it to the local registry,
    and updates the container's buildStatus and buildLog in the database.

    Args:
        container_id: Database ID of the Container to build.

    Returns:
        bool: True if the build and push succeeded, False otherwise.
    """
    build_log_lines = []
    temp_dir = None

    try:
        # Load container data
        with Session() as session:
            container = session.execute(
                select(Container).where(Container.containerId == container_id)
            ).scalar_one_or_none()
            if container is None:
                print(f"[ImageBuilder] Container {container_id} not found")
                return False

            image_name = container.imageName
            base_image = container.baseImage or "ubuntu:22.04"
            username = container.containerUsername or "user"
            dockerfile_body = container.dockerfileCommands
            cmd = container.containerCmd

            # Use default body if none provided
            if not dockerfile_body or not dockerfile_body.strip():
                print(f"[ImageBuilder] Container {container_id} has no dockerfileCommands, skipping")
                return False

            # Mark as building
            container.buildStatus = "building"
            container.buildLog = ""
            session.commit()

        registry_address = settings_handler.get_setting("docker.registryAddress")
        full_tag = f"{registry_address}/{image_name}:latest"

        # Generate Dockerfile
        dockerfile_content = generate_dockerfile(base_image, dockerfile_body, cmd)
        build_log_lines.append(f"=== Building image: {full_tag}")
        build_log_lines.append(f"=== Base image: {base_image}")
        build_log_lines.append(f"=== Container username: {username}")
        build_log_lines.append(f"=== Generated Dockerfile:")
        build_log_lines.append(dockerfile_content)
        build_log_lines.append("=== Starting build...")

        # Write Dockerfile to temp directory
        temp_dir = tempfile.mkdtemp(prefix="cotf_build_")
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        # Build the image with streaming logs
        log_stream = docker.build(
            context_path=temp_dir,
            file=dockerfile_path,
            tags=[full_tag],
            stream_logs=True,
            load=True,
        )

        for log_line in log_stream:
            line = log_line.strip() if isinstance(log_line, str) else str(log_line).strip()
            if line:
                build_log_lines.append(line)
                # Periodically update build log in DB so frontend can poll
                if len(build_log_lines) % 20 == 0:
                    _update_build_log(container_id, "\n".join(build_log_lines))

        build_log_lines.append("=== Build complete, pushing to registry...")
        _update_build_log(container_id, "\n".join(build_log_lines))

        # Push to registry
        push_output = docker.push(full_tag, stream_logs=True)
        if push_output:
            for tag_name, log_bytes in push_output:
                line = log_bytes.decode("utf-8", errors="replace").strip() if isinstance(log_bytes, bytes) else str(log_bytes).strip()
                if line:
                    build_log_lines.append(line)

        build_log_lines.append("=== Push complete. Image built and pushed successfully.")

        # Get image size
        image_size = None
        try:
            inspected = docker.image.inspect(full_tag)
            image_size = inspected.size
            build_log_lines.append(f"=== Image size: {_format_size(image_size)}")
        except Exception:
            pass

        # Mark success
        with Session() as session:
            container = session.execute(
                select(Container).where(Container.containerId == container_id)
            ).scalar_one_or_none()
            if container:
                container.buildStatus = "success"
                container.buildLog = "\n".join(build_log_lines)
                container.imageSize = image_size
                container.lastBuiltAt = datetime.now(timezone.utc)
                session.commit()

        print(f"[ImageBuilder] Successfully built and pushed {full_tag}")
        return True

    except Exception as e:
        error_msg = str(e)
        build_log_lines.append(f"=== BUILD FAILED: {error_msg}")
        build_log_lines.append(traceback.format_exc())

        # Mark failure
        try:
            with Session() as session:
                container = session.execute(
                    select(Container).where(Container.containerId == container_id)
                ).scalar_one_or_none()
                if container:
                    container.buildStatus = "failed"
                    container.buildLog = "\n".join(build_log_lines)
                    session.commit()
        except Exception as db_error:
            print(f"[ImageBuilder] Failed to update build status: {db_error}")

        print(f"[ImageBuilder] Failed to build container {container_id}: {error_msg}")
        return False

    finally:
        # Clean up temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


def _update_build_log(container_id, log_text):
    """Update the build log in the database for progress polling.

    Args:
        container_id: Database ID of the Container.
        log_text: Current accumulated build log text.
    """
    try:
        with Session() as session:
            container = session.execute(
                select(Container).where(Container.containerId == container_id)
            ).scalar_one_or_none()
            if container:
                container.buildLog = log_text
                session.commit()
    except Exception:
        pass  # Non-critical — log update failures shouldn't break the build


def _format_size(size_bytes):
    """Format byte size to human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        str: Formatted size (e.g. "705.5 MB", "1.2 GB").
    """
    if size_bytes is None:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def update_all_image_sizes():
    """Update image sizes for all containers by checking locally available Docker images.

    Lists all Docker images on this host and matches them against container
    definitions in the database by image name. Updates the imageSize column
    for any container whose image is found locally. Called once on daemon startup.
    """
    try:
        registry_address = settings_handler.get_setting("docker.registryAddress")
        images = docker.image.list()

        # Build a map of image tag -> size
        tag_size_map = {}
        for img in images:
            for tag in img.repo_tags:
                tag_size_map[tag] = img.size

        with Session() as session:
            containers = session.execute(
                select(Container).where(Container.removed.isnot(True))
            ).scalars().all()

            updated = 0
            for container in containers:
                full_tag = f"{registry_address}/{container.imageName}:latest"
                size = tag_size_map.get(full_tag)
                if size is not None and size != container.imageSize:
                    container.imageSize = size
                    updated += 1
                elif size is None and container.imageSize is not None:
                    container.imageSize = None
                    updated += 1

            if updated > 0:
                session.commit()
                print(f"[ImageBuilder] Updated image sizes for {updated} container(s)")

    except Exception as e:
        print(f"[ImageBuilder] Failed to update image sizes: {e}")
