#!/bin/bash

################################################################################
### This script installs all requirements for containers on the fly to work. ### 
################################################################################

GREEN='\033[0;32m'
RED='\033[0;31m'
RESET='\033[0m'
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

# Load settings
source "$CURRENT_DIR/user_config/settings"

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
    echo -e "\n${RED}This script must be run with sudo privileges. Please run this with sudo permissions. Exiting.${RESET}"
    exit 1
fi

echo "Running with sudo privileges."

# Update and install initial packages
sudo apt update
sudo apt install -y python3-pip libsasl2-dev libldap2-dev libssl-dev
sudo ubuntu-drivers install nvidia:535-server

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
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
fi

# Install PM2 globally if it's not already installed
if ! command -v pm2 > /dev/null; then
    sudo npm install pm2 -g
    pm2 startup
fi

# Install Nvidia Docker Runtime
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo tee /etc/apt/trusted.gpg.d/nvidia.gpg > /dev/null
curl -fsSL https://nvidia.github.io/nvidia-container-runtime/gpgkey | sudo tee /etc/apt/trusted.gpg.d/nvidia-container-runtime.gpg > /dev/null
curl -fsSL https://nvidia.github.io/nvidia-docker/gpgkey | sudo tee /etc/apt/trusted.gpg.d/nvidia-docker.gpg > /dev/null

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

# Add 127.0.0.1 and server IP address to docker insecure-registry configuration.
# This allows (insecure) HTTP protocol to be used for pushing / pulling with the given IP addresses.
INSECURE_REGISTRY="${SERVER_IP_ADDRESS}:${DOCKER_REGISTRY_PORT}"
LOCAL_REGISTRY="127.0.0.1:${DOCKER_REGISTRY_PORT}"
DOCKER_DAEMON_CONFIG="/etc/docker/daemon.json"
update_docker_daemon_config() {
    # Check if the Docker daemon configuration file exists
    if [ -f "$DOCKER_DAEMON_CONFIG" ]; then
        # Backup the existing configuration file
        cp "$DOCKER_DAEMON_CONFIG" "${DOCKER_DAEMON_CONFIG}.bak"

        # Check if insecure-registries is already in the config
        if grep -q '"insecure-registries"' "$DOCKER_DAEMON_CONFIG"; then
            # Ensure both registries are in the list, avoiding duplicates
            jq --arg local "$LOCAL_REGISTRY" --arg reg "$INSECURE_REGISTRY" '
                .["insecure-registries"] += [$local, $reg] |
                .["insecure-registries"] |= unique
            ' "$DOCKER_DAEMON_CONFIG" > temp.json && mv temp.json "$DOCKER_DAEMON_CONFIG"
        else
            # Add insecure-registries with both registries to the config
            jq --arg local "$LOCAL_REGISTRY" --arg reg "$INSECURE_REGISTRY" '
                . + {"insecure-registries": [$local, $reg]}
            ' "$DOCKER_DAEMON_CONFIG" > temp.json && mv temp.json "$DOCKER_DAEMON_CONFIG"
        fi
    else
        # If the configuraration file did not exist, then create the configuration file with insecure-registries setting
        echo "{\"insecure-registries\" : [\"$LOCAL_REGISTRY\", \"$INSECURE_REGISTRY\"]}" > "$DOCKER_DAEMON_CONFIG"
    fi
}
update_docker_daemon_config

# Add user to docker group
sudo usermod -aG docker $CURRENT_USER

# Start private (local) docker registry
if [ ! "$(sudo -u $CURRENT_USER docker ps -q -f name=registry)" ]; then
    if [ "$(sudo -u $CURRENT_USER docker ps -aq -f status=exited -f name=registry)" ]; then
        # Cleanup any exited registry container
        sudo -u $CURRENT_USER docker rm registry
    fi
    # Start the Docker registry container
    sudo -u $CURRENT_USER docker run -d -p ${DOCKER_REGISTRY_PORT}:5000 --restart=always --name registry registry:2
fi

# Build base-ubuntu image to be used as an example with default setup
sudo -u $CURRENT_USER docker build -t $INSECURE_REGISTRY/ubuntu-base:latest -f DockerfileContainerExample .
sudo -u $CURRENT_USER docker push $INSECURE_REGISTRY/ubuntu-base:latest

# Restart Docker Daemon to apply changes
sudo systemctl restart docker
echo "Docker daemon configuration updated and Docker service restarted."

echo "You need to restart the machine before the Nvidia drivers will work."