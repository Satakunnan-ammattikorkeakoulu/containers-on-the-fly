#!/bin/bash

######
# This script configures the ufw firewall rules for this server.
######

CURRENT_DIR=$(pwd)

# Load settings
source "$CURRENT_DIR/user_config/settings"

# Load server type from temporary file if it exists (for Docker utility setup)
IS_MAIN_SERVER=true  # Default to true for backward compatibility
if [ -f /tmp/containerfly_server_type ]; then
    IS_MAIN_SERVER=$(cat /tmp/containerfly_server_type)
    rm /tmp/containerfly_server_type  # Clean up
fi

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
    echo -e "\n${RED}This script must be run with sudo privileges. Please run this with sudo permissions. Exiting.${RESET}"
    exit 1
fi
echo "Running with sudo privileges."

# Reset all current UFW rules
yes | sudo ufw reset

# Add UFW rules
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

# Common final rules
sudo ufw route allow from any to any
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