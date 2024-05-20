#!/bin/bash

################################################################################
### This script installs all requirements for containers on the fly to work. ### 
################################################################################

# TODO: NGINX
# TODO: MARIADB

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo privileges."
    exit 1
fi

echo "Running with sudo privileges."

# Update and install initial packages
sudo apt update
sudo apt install -y python3-pip libsasl2-dev libldap2-dev libssl-dev
sudo ubuntu-drivers install nvidia:535-server

# Configure Git (this is idempotent, so running it multiple times is fine)
# TODO: Grab from settings file
git config --global user.email "toni.aaltonen@samk.fi"
git config --global user.name "Toni Aaltonen"

# Add Docker's official GPG key if it's not already added
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    sudo apt install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
fi

# Add the Docker repository if it's not already in the sources list
if ! grep -q "^deb .*https://download.docker.com/linux/ubuntu" /etc/apt/sources.list /etc/apt/sources.list.d/*; then
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
fi

# Update repositories and install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Test that docker works
sudo docker run hello-world

# Install Node.js and npm if they are not installed
if ! command -v node > /dev/null || ! command -v npm > /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
fi

# Install PM2 globally if it's not already installed
if ! command -v pm2 > /dev/null; then
    sudo npm install pm2 -g
    pm2 startup
fi

# Install Python requirements (assumes requirements.txt is present)
# TODO: Path should not be absolute
pip install -r /home/aiserver/aiserver/webapp/backend/requirements.txt

# Install Nvidia Docker Runtime
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/nvidia.gpg
curl -fsSL https://nvidia.github.io/nvidia-container-runtime/gpgkey | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/nvidia-container-runtime.gpg
curl -fsSL https://nvidia.github.io/nvidia-docker/gpgkey | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/nvidia-docker.gpg

sudo apt-get update
sudo apt-get install -y nvidia-docker2

# Make sure that apt autoupdate does not update Nvidia drivers.
# If it would update, then Nvidia drivers will stop working until system has been rebooted (not good!)
# Path to the unattended-upgrades configuration file
CONFIG_FILE="/etc/apt/apt.conf.d/50unattended-upgrades"

# Check if the NVIDIA blacklist entry exists
if grep -q "Unattended-Upgrade::Package-Blacklist" "$CONFIG_FILE"; then
    # If the blacklist entry exists, check if nvidia-* is already in the blacklist
    if ! grep -q "\"nvidia-*\";" "$CONFIG_FILE"; then
        # If nvidia-* is not in the blacklist, add it
        sudo sed -i '/Unattended-Upgrade::Package-Blacklist {/a \    "nvidia-*";' "$CONFIG_FILE"
    fi
else
    # If the blacklist entry does not exist, add the entire blacklist block
    sudo sed -i '/^Unattended-Upgrade::Origins-Pattern {/a Unattended-Upgrade::Package-Blacklist {\n    "nvidia-*";\n};' "$CONFIG_FILE"
fi

echo "Unattended upgrades configuration updated successfully."


# Make sure that the Docker can use a local repository, that has no sertificate
sudo apt install -y jq
# Docker Daemon Configuration File
DOCKER_DAEMON_CONFIG="/etc/docker/daemon.json"

# Registry Address
# TODO: Grab from settings file
INSECURE_REGISTRY="10.103.6.20:5000"

# Function to update the Docker daemon configuration
update_docker_daemon_config() {
    # Check if the Docker daemon configuration file exists
    if [ -f "$DOCKER_DAEMON_CONFIG" ]; then
        # Backup the existing configuration file
        cp "$DOCKER_DAEMON_CONFIG" "${DOCKER_DAEMON_CONFIG}.bak"

        # Check if insecure-registries is already in the config
        if grep -q '"insecure-registries"' "$DOCKER_DAEMON_CONFIG"; then
            # Add the registry to the existing array
            jq --arg reg "$INSECURE_REGISTRY" '.["insecure-registries"] += [$reg]' "$DOCKER_DAEMON_CONFIG" > temp.json && mv temp.json "$DOCKER_DAEMON_CONFIG"
        else
            # Add insecure-registries to the config
            jq --arg reg "$INSECURE_REGISTRY" '. + {"insecure-registries": [$reg]}' "$DOCKER_DAEMON_CONFIG" > temp.json && mv temp.json "$DOCKER_DAEMON_CONFIG"
        fi
    else
        # Create the configuration file with insecure-registries
        echo "{\"insecure-registries\" : [\"$INSECURE_REGISTRY\"]}" > "$DOCKER_DAEMON_CONFIG"
    fi
}

# Main execution
update_docker_daemon_config

# Add user to docker group
# TODO: Does this user exist? Have we actually created it yet alongside the group?
# TODO: Does the aiserver user also need root permissions?
sudo usermod -aG docker aiserver

# Restart Docker Daemon to apply changes
sudo systemctl restart docker
echo "Docker daemon configuration updated and Docker service restarted."

echo "You need to restart the machine before the Nvidia drivers will work."