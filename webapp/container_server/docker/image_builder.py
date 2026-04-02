"""Docker image builder for on-the-fly container image creation.

Generates Dockerfiles from admin-provided body, builds the image, and
pushes it to the local registry. Reports progress and results to the
backend via the API client.

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
from helpers.settings_handler import settings_handler
from helpers.logger import log

# Pattern for valid Docker image names
_VALID_IMAGE_NAME_RE = re.compile(r'^[a-zA-Z0-9._/:\-]+$')

# Default CMD instruction for containers
DEFAULT_CMD = '["/bin/bash","-c", "/usr/sbin/sshd -D ;"]'

# Default password command template
DEFAULT_PASSWORD_COMMAND = "/bin/echo '{username}:{password}' | /usr/sbin/chpasswd"

# Default SSH key deployment commands template
DEFAULT_SSH_KEY_DEPLOY_COMMANDS = """mkdir -p /home/{username}/.ssh && chmod 700 /home/{username}/.ssh
cat <<'SSHEOF' > /home/{username}/.ssh/authorized_keys
{ssh_key}
SSHEOF
chmod 600 /home/{username}/.ssh/authorized_keys && chown -R {username}:$(id -gn {username}) /home/{username}/.ssh"""


def get_default_dockerfile_body(username="user"):
    """Get the default Dockerfile body with the given username interpolated.

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

# Create containerfly group (GID 5620)
RUN groupadd -g 5620 containerfly

# Create user '{username}' with containerfly as primary group
RUN useradd -rm -d /home/{username} -s /bin/bash -g containerfly -G sudo -u 1000 {username}
RUN echo '{username}:password' | chpasswd

# Configure SSH server
RUN sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config && \\
    sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \\
    mkdir /var/run/sshd
RUN service ssh start

USER {username}
WORKDIR /home/{username}
USER root
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


def build_and_push_image(container_data, api_client):
    """Build a Docker image for a container definition and push to registry.

    Args:
        container_data: Dict with containerId, imageName, baseImage,
            dockerfileCommands, containerUsername, containerCmd.
        api_client: DaemonApiClient instance for reporting progress.

    Returns:
        bool: True if the build and push succeeded, False otherwise.
    """
    container_id = container_data["containerId"]
    image_name = container_data["imageName"]
    base_image = container_data.get("baseImage") or "ubuntu:22.04"
    username = container_data.get("containerUsername") or "user"
    dockerfile_body = container_data.get("dockerfileCommands")
    cmd = container_data.get("containerCmd")

    if not dockerfile_body or not dockerfile_body.strip():
        log.info(f"Container {container_id} has no dockerfileCommands, skipping")
        return False

    build_log_lines = []
    temp_dir = None

    try:
        # Mark as building
        api_client.report_build_progress(container_id, "Starting build...")

        build_start_time = datetime.now(timezone.utc)
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
                if len(build_log_lines) % 20 == 0:
                    api_client.report_build_progress(container_id, "\n".join(build_log_lines))

        build_log_lines.append("=== Build complete, pushing to registry...")
        api_client.report_build_progress(container_id, "\n".join(build_log_lines))

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

        build_duration = datetime.now(timezone.utc) - build_start_time
        build_log_lines.append(f"=== Build completed in {_format_duration(build_duration)}")

        # Report success
        api_client.report_build_complete(container_id, {
            "buildStatus": "success",
            "buildLog": "\n".join(build_log_lines),
            "imageSize": image_size,
            "lastBuiltAt": datetime.now(timezone.utc).isoformat(),
        })

        log.info(f"Successfully built and pushed {full_tag}")
        return True

    except Exception as e:
        error_msg = str(e)
        build_log_lines.append(f"=== BUILD FAILED: {error_msg}")
        build_log_lines.append(traceback.format_exc())

        try:
            api_client.report_build_complete(container_id, {
                "buildStatus": "failed",
                "buildLog": "\n".join(build_log_lines),
            })
        except Exception as report_error:
            log.error(f"Failed to report build failure for container {container_id}: {report_error}")

        log.error(f"Failed to build container {container_id}: {error_msg}")
        return False

    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


def remove_image(container_data, api_client):
    """Remove a Docker image for a container that has been deleted.

    Args:
        container_data: Dict with containerId and imageName.
        api_client: DaemonApiClient instance for reporting.

    Returns:
        bool: True if the image was removed, False on error.
    """
    container_id = container_data["containerId"]
    image_name = container_data["imageName"]

    try:
        registry_address = settings_handler.get_setting("docker.registryAddress")
        full_tag = f"{registry_address}/{image_name}:latest"

        try:
            docker.image.remove(full_tag, force=True)
            log.info(f"Removed Docker image {full_tag}")
        except Exception as e:
            log.warning(f"Image {full_tag} not found locally, skipping removal: {e}")

        api_client.report_image_removed(container_id, "removed")
        return True

    except Exception as e:
        log.error(f"Failed to remove image for container {container_id}: {e}")
        return False


def update_all_image_sizes(api_client):
    """Update image sizes by checking locally available Docker images.

    Lists all Docker images on this host and reports their sizes to the
    backend via batch API call. Called once on daemon startup.

    Args:
        api_client: DaemonApiClient instance for reporting.
    """
    try:
        registry_address = settings_handler.get_setting("docker.registryAddress")
        images = docker.image.list()

        # Build a map of image tag -> size
        tag_size_map = {}
        for img in images:
            for tag in img.repo_tags:
                tag_size_map[tag] = img.size

        # Build batch update list -- extract image name from full tag
        batch = []
        prefix = f"{registry_address}/"
        for tag, size in tag_size_map.items():
            if tag.startswith(prefix) and tag.endswith(":latest"):
                image_name = tag[len(prefix):-len(":latest")]
                batch.append({"imageName": image_name, "imageSize": size})

        if batch:
            api_client.update_image_sizes_batch(batch)
            log.info(f"Reported image sizes for {len(batch)} image(s)")

    except Exception as e:
        log.error(f"Failed to update image sizes: {e}")


def _format_size(size_bytes):
    """Format byte size to human-readable string."""
    if size_bytes is None:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _format_duration(delta):
    """Format a timedelta to a human-readable string."""
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"
