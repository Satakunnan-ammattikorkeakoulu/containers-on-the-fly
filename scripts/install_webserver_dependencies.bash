#!/bin/bash

##########################################################################################
### This script installs all requirements for the web servers to work on this machine. ### 
##########################################################################################

GREEN='\033[0;32m'
RED='\033[0;31m'
RESET='\033[0m'
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

# Load settings
source "$CURRENT_DIR/user_config/settings"

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}This script must be run with sudo privileges.${RESET}"
    exit 1
fi

echo "Running with sudo privileges."

# Update and install initial packages
sudo apt update

# Install required libraries
sudo apt --assume-yes install python3 python3-pip libldap2-dev libsasl2-dev libssl-dev
sudo apt --assume-yes install python3-ldap

# Function to check if Nginx is installed
check_nginx_installed() {
    if dpkg -l | grep -q nginx; then
        echo "Nginx is already installed."
        return 0
    else
        echo "Nginx is not installed."
        return 1
    fi
}

# Function to install Nginx
install_nginx() {
    echo "Updating package list..."
    
    echo "Installing Nginx..."
    apt install -y nginx

    if [ $? -eq 0 ]; then
        echo "Nginx installed successfully."
    else
        echo -e "${RED}Failed to install Nginx.${RESET}"
        exit 1
    fi
}

# Check if Nginx is installed
check_nginx_installed
if [ $? -ne 0 ]; then
    install_nginx
fi

CUSTOM_CONF="$CURRENT_DIR/user_config/nginx_settings.conf"

# Add custom configuration to nginx.conf if not already present
NGINX_CONF="/etc/nginx/nginx.conf"
if ! grep -q "include $CUSTOM_CONF;" $NGINX_CONF; then
    echo "Adding custom configuration to Nginx main configuration..."
    sudo sed -i "/http {/a \\    include $CUSTOM_CONF;" $NGINX_CONF
else
    echo -e "${GREEN}Custom configuration is already included in Nginx main configuration.${RESET}"
fi

# Disable the default site
if [ -L /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
    echo -e "${GREEN}Default nginx site configuration disabled.${RESET}"
fi

# Test and reload Nginx
nginx -t
if [ $? -eq 0 ]; then
    systemctl reload nginx
    echo -e "${GREEN}Nginx configuration seems to be fine.${RESET}"
else
    echo -e "${RED}Nginx configuration test failed. Please check the configuration.${RESET}"
    exit 1
fi

# Ensure Nginx starts on boot and start Nginx
systemctl enable nginx
systemctl start nginx
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Nginx is now running and enabled to start on boot.${RESET}"
else
    echo -e "${RED}Failed to start Nginx.${RESET}"
    exit 1
fi

# Check if Nginx is active and enabled
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}Nginx is active.${RESET}"
else
    echo -e "${RED}Nginx is not running.${RESET}"
fi

if systemctl is-enabled --quiet nginx; then
    echo -e "${GREEN}Nginx is enabled to start on boot.${RESET}"
else
    echo -e "${RED}Nginx is not enabled to start on boot.${RESET}"
fi

# Check if MariaDB is installed
check_mariadb_installed() {
    if dpkg -l | grep -q mariadb; then
        echo -e "${GREEN}MariaDB is already installed.${RESET}"
        return 0
    else
        echo -e "${RED}MariaDB is not installed.${RESET}"
        return 1
    fi
}

# Function to install MariaDB
install_mariadb() {
    echo "Installing MariaDB..."
    apt install -y mariadb-server mariadb-client

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}MariaDB installed successfully.${RESET}"
    else
        echo -e "${RED}Failed to install MariaDB.${RESET}"
        exit 1
    fi
}

# Check if MariaDB is installed
check_mariadb_installed
if [ $? -ne 0 ]; then
    install_mariadb
fi

# Allow MariaDB to listen on all interfaces to allow remote connections
# Don't worry, we have disabled by default all incoming connections to ports with UFW before this.
# We just need to do this to in the future allow remote connections from possible container servers.
sudo sed -i 's/^bind-address\s*=.*$/bind-address = 0.0.0.0/' "/etc/mysql/mariadb.conf.d/50-server.cnf"

# Ensure MariaDB starts on boot and start the service
sudo systemctl enable mariadb
sudo systemctl start mariadb
if [ $? -eq 0 ]; then
    echo -e "${GREEN}MariaDB is now running and enabled to start on boot.${RESET}"
else
    echo -e "${RED}Failed to start MariaDB.${RESET}"
    exit 1
fi

# Check if database exists
RESULT=$(mysql -e "SHOW DATABASES LIKE '$MARIADB_DB_NAME';" 2>/dev/null | grep "$MARIADB_DB_NAME" > /dev/null; echo "$?")
if [ $RESULT -eq 0 ]; then
  echo "Database '$MARIADB_DB_NAME' already exists. Continuing."
else
  echo "Database '$MARIADB_DB_NAME' does not exist."
  mysql -e "CREATE DATABASE IF NOT EXISTS $MARIADB_DB_NAME;"
  echo -e "${GREEN}Database ${MARIADB_DB_NAME} was created successfully.${RESET}"
fi

# Check if user exists
RESULT=$(mysql -sse "SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = '$MARIADB_DB_USER');")

if [ "$RESULT" -eq 1 ]; then
  echo "User '$MARIADB_DB_USER' already exists. Continuing."
else
  echo "User '$MARIADB_DB_USER' does not exist."
  mysql -e "CREATE USER IF NOT EXISTS '$MARIADB_DB_USER'@'%' IDENTIFIED BY '$MARIADB_DB_USER_PASSWORD';"
  mysql -e "GRANT ALL PRIVILEGES ON $MARIADB_DB_NAME.* TO '$MARIADB_DB_USER'@'%';"
  mysql -e "FLUSH PRIVILEGES;"
  echo -e "${GREEN}In mariadb/mysql, created the user ${MARIADB_DB_USER} and granted the user full access to the database ${MARIADB_DB_NAME}."
fi

# Check if Node.js and npm are installed
check_node_installed() {
    if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
        echo -e "${GREEN}Node.js and npm are already installed.${RESET}"
        return 0
    else
        echo -e "${RED}Node.js and npm are not installed.${RESET}"
        return 1
    fi
}

# Function to install Node.js and npm
install_node() {
    echo "Installing Node.js and npm..."
    curl -sL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Node.js and npm installed successfully.${RESET}"
    else
        echo -e "${RED}Failed to install Node.js and npm.${RESET}"
        exit 1
    fi
}

# Check if Node.js and npm are installed
check_node_installed
if [ $? -ne 0 ]; then
    install_node
fi

# Install PM2 globally if it's not already installed
if ! command -v pm2 > /dev/null; then
    sudo npm install pm2 -g
    pm2 startup
fi