"""Default Dockerfile templates and container command constants.

Provides the default Dockerfile body, CMD instruction, password command,
and SSH key deployment commands used by admin endpoints when creating
or editing container definitions.
"""

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
