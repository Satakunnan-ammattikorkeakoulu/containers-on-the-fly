#!/bin/bash

######
# This script configures the ufw firewall rules for this server.
######

CURRENT_DIR=$(pwd)

# Load settings
source "$CURRENT_DIR/user_config/settings"

# Load server type from temporary file if it exists (for Docker utility setup)
IS_MAIN_SERVER=true  # Default to true for backward compatibility
if [ -f .server_type ]; then
    IS_MAIN_SERVER=$(cat "${CURRENT_DIR}/.server_type")
fi

# Validate required variables and set defaults
if [ -z "$DOCKER_REGISTRY_PORT" ]; then
    echo "Warning: DOCKER_REGISTRY_PORT not set, using default: 5000"
    DOCKER_REGISTRY_PORT=5000
fi

if [ -z "$SERVER_IP_ADDRESS" ] || [ "$SERVER_IP_ADDRESS" = "YOUR_IP_HERE" ]; then
    echo "Error: SERVER_IP_ADDRESS not properly configured."
    echo "Current value: '$SERVER_IP_ADDRESS'"
    echo "Please check your user_config/settings file and ensure SERVER_IP_ADDRESS is set correctly."
    exit 1
fi

# Convert localhost to 127.0.0.1 for UFW compatibility
if [ "$SERVER_IP_ADDRESS" = "localhost" ]; then
    echo "Converting localhost to 127.0.0.1 for UFW compatibility"
    SERVER_IP_ADDRESS="127.0.0.1"
fi

# Validate IP address format
if ! [[ $SERVER_IP_ADDRESS =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    echo "Error: SERVER_IP_ADDRESS must be a valid IP address, got: '$SERVER_IP_ADDRESS'"
    echo "Converting to 127.0.0.1 for local access"
    SERVER_IP_ADDRESS="127.0.0.1"
fi

echo "SERVER_IP_ADDRESS='$SERVER_IP_ADDRESS'"
echo "DOCKER_REGISTRY_PORT='$DOCKER_REGISTRY_PORT'"

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
    echo -e "\n${RED}This script must be run with sudo privileges. Please run this with sudo permissions. Exiting.${RESET}"
    exit 1
fi
echo "Running with sudo privileges."

# Reset all UFW rules
yes | sudo ufw reset

# Remove existing Docker UFW rules to prevent duplicates
sudo sed -i '/# BEGIN UFW AND DOCKER/,/# END UFW AND DOCKER/d' /etc/ufw/after.rules

# Set defaults
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH is always needed
sudo ufw allow 22

# Container ports are always needed
sudo ufw allow $DOCKER_RESERVATION_PORT_RANGE_START:$DOCKER_RESERVATION_PORT_RANGE_END/tcp
sudo ufw allow $DOCKER_RESERVATION_PORT_RANGE_START:$DOCKER_RESERVATION_PORT_RANGE_END/udp

# Allow additional custom ports if specified
if [ -n "$FIREWALL_ADDITIONAL_PORTS" ]; then
    IFS=',' read -ra PORTS <<< "$FIREWALL_ADDITIONAL_PORTS"
    for port in "${PORTS[@]}"; do
        port=$(echo "$port" | tr -d ' ')  # Remove spaces
        if [[ "$port" =~ ^[0-9]+$ ]]; then  # Validate it's a number
            echo "Allowing additional port: $port"
            sudo ufw allow $port
        fi
    done
fi

# Main server specific rules
if [ "$IS_MAIN_SERVER" = "true" ]; then
    echo "Configuring main server firewall rules..."
    # Web interface ports
    sudo ufw allow 80
    sudo ufw allow 443
    # Docker registry rules
    sudo ufw allow from 127.0.0.1 to any port $DOCKER_REGISTRY_PORT
    sudo ufw allow from $SERVER_IP_ADDRESS to any port $DOCKER_REGISTRY_PORT
    sudo ufw route allow from $SERVER_IP_ADDRESS to any port $DOCKER_REGISTRY_PORT
    sudo ufw route deny from any to any port $DOCKER_REGISTRY_PORT
else
    echo "Configuring container server firewall rules..."
fi

# Common final rules - Remove the overly restrictive route deny rule
# The default routing policy is already set to deny above
#sudo ufw route deny from any to any  # This was blocking MariaDB access
#sudo ufw route allow from any to any port $DOCKER_RESERVATION_PORT_RANGE_START:$DOCKER_RESERVATION_PORT_RANGE_END/tcp  # Only allow container ports TCP
#sudo ufw route allow from any to any port $DOCKER_RESERVATION_PORT_RANGE_START:$DOCKER_RESERVATION_PORT_RANGE_END/udp  # Only allow container ports UDP

# Enable (start) the UFW firewall
yes | sudo ufw enable

# Apply Docker specific UFW firewall rules if not applied yet
# These are taken from here: https://github.com/chaifeng/ufw-docker
{
    echo "# BEGIN UFW AND DOCKER"
    echo "*filter"
    echo ":ufw-user-forward - [0:0]"
    echo ":ufw-docker-logging-deny - [0:0]"
    echo ":DOCKER-USER - [0:0]"
    echo "-A DOCKER-USER -j ufw-user-forward"
    echo "-A DOCKER-USER -j RETURN -s 10.0.0.0/8"
    echo "-A DOCKER-USER -j RETURN -s 172.16.0.0/12"
    echo "-A DOCKER-USER -j RETURN -s 192.168.0.0/16"
    echo "-A DOCKER-USER -p udp -m udp --sport 53 --dport 1024:65535 -j RETURN"
    echo "-A DOCKER-USER -j ufw-docker-logging-deny -p tcp -m tcp --tcp-flags FIN,SYN,RST,ACK SYN -d 192.168.0.0/16"
    echo "-A DOCKER-USER -j ufw-docker-logging-deny -p tcp -m tcp --tcp-flags FIN,SYN,RST,ACK SYN -d 10.0.0.0/8"
    echo "-A DOCKER-USER -j ufw-docker-logging-deny -p tcp -m tcp --tcp-flags FIN,SYN,RST,ACK SYN -d 172.16.0.0/12"
    echo "-A DOCKER-USER -j ufw-docker-logging-deny -p udp -m udp --dport 0:32767 -d 192.168.0.0/16"
    echo "-A DOCKER-USER -j ufw-docker-logging-deny -p udp -m udp --dport 0:32767 -d 10.0.0.0/8"
    echo "-A DOCKER-USER -j ufw-docker-logging-deny -p udp -m udp --dport 0:32767 -d 172.16.0.0/12"
    echo "-A DOCKER-USER -j RETURN"
    echo "-A ufw-docker-logging-deny -m limit --limit 3/min --limit-burst 10 -j LOG --log-prefix \"[UFW DOCKER BLOCK] \""
    echo "-A ufw-docker-logging-deny -j DROP"
    echo "COMMIT"
    echo "# END UFW AND DOCKER"
} | sudo tee -a "/etc/ufw/after.rules" > /dev/null

# Print final configuration
echo ""
echo "Firewall configured successfully!"
if [ "$IS_MAIN_SERVER" = "true" ]; then
    echo "Main server ports opened:"
    echo "  - SSH (22)"
    echo "  - HTTP (80)"
    echo "  - HTTPS (443)"
    echo "  - Docker Registry ($DOCKER_REGISTRY_PORT)"
    echo "  - Container ports ($DOCKER_RESERVATION_PORT_RANGE_START-$DOCKER_RESERVATION_PORT_RANGE_END)"
else
    echo "Container server ports opened:"
    echo "  - SSH (22)"
    echo "  - Container ports ($DOCKER_RESERVATION_PORT_RANGE_START-$DOCKER_RESERVATION_PORT_RANGE_END)"
fi
if [ -n "$FIREWALL_ADDITIONAL_PORTS" ]; then
    echo "  - Additional ports: $FIREWALL_ADDITIONAL_PORTS"
fi
echo "All other incoming connections will be blocked."