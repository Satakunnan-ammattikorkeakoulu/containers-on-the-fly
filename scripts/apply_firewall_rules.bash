#!/bin/bash

######
# This script configures the ufw firewall rules for this server.
######

CURRENT_DIR=$(pwd)

# Load settings
source "$CURRENT_DIR/user_config/settings"


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
sudo ufw allow from 127.0.0.1 to any port $DOCKER_REGISTRY_PORT
sudo ufw allow from $SERVER_IP_ADDRESS to any port $DOCKER_REGISTRY_PORT
sudo ufw route allow from $SERVER_IP_ADDRESS to any port $DOCKER_REGISTRY_PORT
sudo ufw route deny from any to any port $DOCKER_REGISTRY_PORT
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow $DOCKER_RESERVATION_PORT_RANGE_START:$DOCKER_RESERVATION_PORT_RANGE_END/tcp
sudo ufw allow $DOCKER_RESERVATION_PORT_RANGE_START:$DOCKER_RESERVATION_PORT_RANGE_END/udp
sudo ufw route allow from any to any
yes | sudo ufw enable

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

# Apply Docker specific UFW firewall rules if not applied yet
# These are taken from here: https://github.com/chaifeng/ufw-docker
# By default Docker allows all connections to Docker containers and with this setup, anyone could access our
# private docker registry (push & pull images). With this setup we can disallow accessing the private docker registry from other locations.

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