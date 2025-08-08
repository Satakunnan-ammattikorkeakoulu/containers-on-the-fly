#!/bin/bash

################################################################################
### This script installs all requirements for containers on the fly to work. ### 
################################################################################

GREEN='\033[0;32m'
RED='\033[0;31m'
RESET='\033[0m'
CURRENT_DIR=$(pwd)

# Robust user detection that works with sudo
CURRENT_USER=${SUDO_USER:-$(logname 2>/dev/null || whoami)}
echo "Detected user: $CURRENT_USER"

# Load settings
source "$CURRENT_DIR/user_config/settings"

# Handle DOCKER_REGISTRY_ADDRESS default - use SERVER_IP_ADDRESS if empty or placeholder
if [ "$DOCKER_REGISTRY_ADDRESS" = "YOUR_IP_HERE" ] || [ -z "$DOCKER_REGISTRY_ADDRESS" ]; then
    if [ -n "$SERVER_IP_ADDRESS" ] && [ "$SERVER_IP_ADDRESS" != "YOUR_IP_HERE" ]; then
        echo -e "\n${YELLOW}DOCKER_REGISTRY_ADDRESS not set, using SERVER_IP_ADDRESS: $SERVER_IP_ADDRESS${RESET}"
        DOCKER_REGISTRY_ADDRESS="$SERVER_IP_ADDRESS"
    else
        echo -e "\n${RED}Error: Both DOCKER_REGISTRY_ADDRESS and SERVER_IP_ADDRESS are not configured in user_config/settings${RESET}"
        echo "Please run the setup process first to configure the server IP address."
        exit 1
    fi
fi

# Function to wait for Docker to be ready
wait_for_docker() {
    local max_attempts=30
    local attempt=1
    
    echo "Waiting for Docker to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if sudo docker info >/dev/null 2>&1; then
            echo "Docker is ready."
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: Docker not ready yet, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "Error: Docker failed to become ready after $max_attempts attempts"
    return 1
}

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
    echo -e "\n${RED}This script must be run with sudo privileges. Please run this with sudo permissions. Exiting.${RESET}"
    exit 1
fi

echo "Running with sudo privileges."

# Update and install initial packages
sudo apt update -qq
sudo rm /etc/apt/sources.list.d/nvidia-*.list 2>/dev/null
sudo apt-get purge -y -qq '^nvidia-.*' '^libnvidia-.*' '^cuda-.*' '^libcuda.*' '^nv.*' 2>/dev/null




# libnvidia-container key
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/nvidia-container.gpg > /dev/null
# nvidia-container-runtime key
curl -fsSL https://nvidia.github.io/nvidia-container-runtime/gpgkey | \
  gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/nvidia-container-runtime.gpg > /dev/null
# nvidia-docker key
curl -fsSL https://nvidia.github.io/nvidia-docker/gpgkey | \
  gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/nvidia-docker.gpg > /dev/null

sudo add-apt-repository ppa:graphics-drivers/ppa -y
sudo apt update -qq

sudo apt install -y -qq python3-pip libsasl2-dev libldap2-dev libssl-dev acl

# Create containerfly group if it doesn't exist
if ! getent group containerfly > /dev/null 2>&1; then
    echo "Creating containerfly group with GID 5620..."
    sudo groupadd -g 5620 containerfly
    echo -e "${GREEN}Group 'containerfly' created with GID 5620.${RESET}"
else
    echo -e "${GREEN}Group 'containerfly' already exists.${RESET}"
fi

sudo ubuntu-drivers install nvidia:570-server #-qq >/dev/null 2>&1

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
sudo apt update -qq
sudo apt install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Test that docker works and cleanup
sudo docker run --rm hello-world >/dev/null 2>&1

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

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting NVIDIA Container Toolkit installation and configuration..."

echo "1/5: Adding NVIDIA Container Toolkit repository..."

# Remove existing keyring if it exists to avoid prompts
sudo rm -f /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
if [ $? -ne 0 ]; then
    echo "Error: Failed to download GPG key for NVIDIA Container Toolkit. Exiting."
    exit 1
fi
echo "NVIDIA GPG key added."

curl -s -L "https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list" | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null
if [ $? -ne 0 ]; then
    echo "Error: Failed to add NVIDIA Container Toolkit repository list. Exiting."
    exit 1
fi
echo "NVIDIA Container Toolkit repository added."

echo "2/5: Updating apt package cache..."
sudo apt-get update -qq
if [ $? -ne 0 ]; then
    echo "Error: Failed to update apt cache. Exiting."
    exit 1
fi
echo "Apt cache updated."

echo "3/5: Installing nvidia-container-toolkit..."
sudo apt-get install -y -qq nvidia-container-toolkit
if [ $? -ne 0 ]; then
    echo "Error: Failed to install nvidia-container-toolkit. Exiting."
    exit 1
fi
echo "nvidia-container-toolkit installed."

echo "4/5: Configuring Docker to use the NVIDIA runtime..."
sudo nvidia-ctk runtime configure --runtime=docker
if [ $? -ne 0 ]; then
    echo "Error: Failed to configure Docker runtime. Exiting."
    exit 1
fi
echo "Docker runtime configured for NVIDIA."

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
sudo apt install -y -qq jq
# Docker Daemon Configuration File
DOCKER_DAEMON_CONFIG="/etc/docker/daemon.json"

# Add 127.0.0.1 and server IP address to docker insecure-registry configuration.
# This allows (insecure) HTTP protocol to be used for pushing / pulling with the given IP addresses.
INSECURE_REGISTRY="${DOCKER_REGISTRY_ADDRESS}:${DOCKER_REGISTRY_PORT}"
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
echo "Updating Docker daemon configuration..."
update_docker_daemon_config

# Add user to docker group
echo "Adding user to docker group..."
sudo usermod -aG docker $CURRENT_USER

# CONSOLIDATED RESTART: Only restart Docker once after all configuration is complete
echo "5/5: Restarting Docker daemon with all configuration changes..."
sudo systemctl restart docker
if [ $? -ne 0 ]; then
    echo "Error: Failed to restart Docker daemon. Exiting."
    exit 1
fi

# Wait for Docker to be fully ready before proceeding
wait_for_docker
if [ $? -ne 0 ]; then
    echo "Error: Docker is not responding after restart. Exiting."
    exit 1
fi

echo "Docker daemon restarted successfully and is ready."
echo "NVIDIA Container Toolkit installation and configuration complete."

echo "Starting private (local) docker registry (only on main server)"
# Start private (local) docker registry (only on main server)
IS_MAIN_SERVER=$(cat "${CURRENT_DIR}/.server_type" 2>/dev/null || echo "false")
if [ "$IS_MAIN_SERVER" = "true" ]; then
    echo "This is main server, starting private (local) docker registry..."
    if [ ! "$(sudo -u $CURRENT_USER docker ps -q -f name=registry)" ]; then
        if [ "$(sudo -u $CURRENT_USER docker ps -aq -f status=exited -f name=registry)" ]; then
            # Cleanup any exited registry container
            sudo -u $CURRENT_USER docker rm registry
        fi
        # Start the Docker registry container
        sudo -u $CURRENT_USER docker run -d -p ${DOCKER_REGISTRY_PORT}:5000 --restart=always --name registry registry:2
    fi

    # Wait a moment for registry to start
    echo "Waiting for registry to be ready..."
    sleep 5

    # Build base-ubuntu image to be used as an example with default setup
    sudo -u $CURRENT_USER docker build -t $INSECURE_REGISTRY/ubuntu-base:latest -f DockerfileContainerExample .
    sudo -u $CURRENT_USER docker push $INSECURE_REGISTRY/ubuntu-base:latest
else
    echo "Container server detected - skipping Docker registry setup (will connect to main server registry)"
fi

echo "Docker daemon configuration updated and Docker service is running."
echo "You need to restart the machine before the Nvidia drivers will work."