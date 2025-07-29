#!/bin/bash

######
# This script configures the iptables firewall rules for this server.
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

# Convert localhost to 127.0.0.1 for compatibility
if [ "$SERVER_IP_ADDRESS" = "localhost" ]; then
    echo "Converting localhost to 127.0.0.1 for compatibility"
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

# Install iptables-persistent for rule persistence
if ! dpkg -l | grep -q "^ii.*iptables-persistent"; then
    echo "Installing iptables-persistent for automatic rule restoration..."
    # Pre-answer the interactive questions: save current rules
    echo iptables-persistent iptables-persistent/autosave_v4 boolean true | debconf-set-selections
    echo iptables-persistent iptables-persistent/autosave_v6 boolean true | debconf-set-selections
    DEBIAN_FRONTEND=noninteractive apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq iptables-persistent
    
    # Enable and start the service
    systemctl enable netfilter-persistent
    systemctl start netfilter-persistent
    echo "iptables-persistent installed and enabled"
else
    echo "iptables-persistent already installed"
fi

# Flush all existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

# Set default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Allow established and related connections
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# SSH is always needed
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Container ports are always needed
iptables -A INPUT -p tcp --dport $DOCKER_RESERVATION_PORT_RANGE_START:$DOCKER_RESERVATION_PORT_RANGE_END -j ACCEPT
iptables -A INPUT -p udp --dport $DOCKER_RESERVATION_PORT_RANGE_START:$DOCKER_RESERVATION_PORT_RANGE_END -j ACCEPT

# Allow additional custom ports if specified
if [ -n "$FIREWALL_ADDITIONAL_PORTS" ]; then
    IFS=',' read -ra PORTS <<< "$FIREWALL_ADDITIONAL_PORTS"
    for port in "${PORTS[@]}"; do
        port=$(echo "$port" | tr -d ' ')  # Remove spaces
        if [[ "$port" =~ ^[0-9]+$ ]]; then  # Validate it's a number
            echo "Allowing additional port: $port"
            iptables -A INPUT -p tcp --dport $port -j ACCEPT
            iptables -A INPUT -p udp --dport $port -j ACCEPT
        fi
    done
fi

# Main server specific rules
if [ "$IS_MAIN_SERVER" = "true" ]; then
    echo "Configuring main server firewall rules..."
    
    # Web interface ports
    iptables -A INPUT -p tcp --dport 80 -j ACCEPT
    iptables -A INPUT -p tcp --dport 443 -j ACCEPT
    
    # Docker registry access control (port 5000)
    echo "Configuring Docker registry access control..."
    # Allow localhost and server IP to access Docker registry
    iptables -A INPUT -s 127.0.0.1 -p tcp --dport $DOCKER_REGISTRY_PORT -j ACCEPT
    iptables -A INPUT -s 127.0.0.1 -p udp --dport $DOCKER_REGISTRY_PORT -j ACCEPT
    iptables -A INPUT -s $SERVER_IP_ADDRESS -p tcp --dport $DOCKER_REGISTRY_PORT -j ACCEPT
    iptables -A INPUT -s $SERVER_IP_ADDRESS -p udp --dport $DOCKER_REGISTRY_PORT -j ACCEPT
    
    # Configure DOCKER-USER chain for container access control
    iptables -N DOCKER-USER 2>/dev/null || true
    iptables -I FORWARD 1 -j DOCKER-USER
    
    # Clean up existing Docker registry rules
    iptables -D DOCKER-USER -p tcp --dport $DOCKER_REGISTRY_PORT -j DROP 2>/dev/null || true
    iptables -D DOCKER-USER -p udp --dport $DOCKER_REGISTRY_PORT -j DROP 2>/dev/null || true
    iptables -D DOCKER-USER -s $SERVER_IP_ADDRESS -p tcp --dport $DOCKER_REGISTRY_PORT -j ACCEPT 2>/dev/null || true
    iptables -D DOCKER-USER -s $SERVER_IP_ADDRESS -p udp --dport $DOCKER_REGISTRY_PORT -j ACCEPT 2>/dev/null || true
    iptables -D DOCKER-USER -s 127.0.0.1 -p tcp --dport $DOCKER_REGISTRY_PORT -j ACCEPT 2>/dev/null || true
    iptables -D DOCKER-USER -s 127.0.0.1 -p udp --dport $DOCKER_REGISTRY_PORT -j ACCEPT 2>/dev/null || true
    
    # Add rules in correct order: ACCEPT rules first, then DROP rules
    iptables -I DOCKER-USER -s 127.0.0.1 -p tcp --dport $DOCKER_REGISTRY_PORT -j ACCEPT
    iptables -I DOCKER-USER -s 127.0.0.1 -p udp --dport $DOCKER_REGISTRY_PORT -j ACCEPT
    iptables -I DOCKER-USER -s $SERVER_IP_ADDRESS -p tcp --dport $DOCKER_REGISTRY_PORT -j ACCEPT
    iptables -I DOCKER-USER -s $SERVER_IP_ADDRESS -p udp --dport $DOCKER_REGISTRY_PORT -j ACCEPT
    iptables -A DOCKER-USER -p tcp --dport $DOCKER_REGISTRY_PORT -j DROP
    iptables -A DOCKER-USER -p udp --dport $DOCKER_REGISTRY_PORT -j DROP
    
    # Always allow DOCKER-USER to return to FORWARD chain at the end
    iptables -A DOCKER-USER -j RETURN
else
    echo "Configuring container server firewall rules..."
fi

# Docker FORWARD rules - allow container traffic
iptables -A FORWARD -i docker0 -o docker0 -j ACCEPT
iptables -A FORWARD -i docker0 ! -o docker0 -j ACCEPT
iptables -A FORWARD -o docker0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Save all iptables rules for persistence
echo "Saving iptables rules for automatic restoration on reboot..."
mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4
echo "Firewall rules saved successfully"

# Print final configuration
echo ""
echo "Firewall configured successfully with iptables!"
if [ "$IS_MAIN_SERVER" = "true" ]; then
    echo "Main server ports opened:"
    echo "  - SSH (22)"
    echo "  - HTTP (80)"
    echo "  - HTTPS (443)"
    echo "  - Docker Registry ($DOCKER_REGISTRY_PORT) - restricted to localhost and $SERVER_IP_ADDRESS"
    echo "  - Container ports ($DOCKER_RESERVATION_PORT_RANGE_START-$DOCKER_RESERVATION_PORT_RANGE_END)"
else
    echo "Container server ports opened:"
    echo "  - SSH (22)"
    echo "  - Container ports ($DOCKER_RESERVATION_PORT_RANGE_START-$DOCKER_RESERVATION_PORT_RANGE_END)"
fi
if [ -n "$FIREWALL_ADDITIONAL_PORTS" ]; then
    echo "  - Additional ports: $FIREWALL_ADDITIONAL_PORTS"
fi
echo "All other incoming connections are blocked by default."
echo "Rules saved to /etc/iptables/rules.v4 and will be restored automatically on reboot."