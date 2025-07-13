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

# Function to check if Caddy is installed
check_caddy_installed() {
    if command -v caddy >/dev/null 2>&1; then
        echo -e "${GREEN}Caddy is already installed.${RESET}"
        return 0
    else
        echo "Caddy is not installed."
        return 1
    fi
}

# Function to install Caddy
install_caddy() {
    echo "Installing Caddy..."
    
    # Install Caddy from official repository
    sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt update
    sudo apt install -y caddy

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Caddy installed successfully.${RESET}"
    else
        echo -e "${RED}Failed to install Caddy.${RESET}"
        exit 1
    fi
}

# Check if Caddy is installed
check_caddy_installed
if [ $? -ne 0 ]; then
    install_caddy
fi

CADDYFILE_PATH="$CURRENT_DIR/user_config/Caddyfile"

# Copy Caddyfile to standard location
if [ -f "$CADDYFILE_PATH" ]; then
    sudo cp "$CADDYFILE_PATH" /etc/caddy/Caddyfile
    echo -e "${GREEN}Caddyfile copied to /etc/caddy/Caddyfile${RESET}"
else
    echo -e "${RED}Caddyfile not found at $CADDYFILE_PATH. Please ensure apply-settings has been run.${RESET}"
    exit 1
fi

# Set proper permissions for Caddyfile
sudo chown root:root /etc/caddy/Caddyfile
sudo chmod 644 /etc/caddy/Caddyfile

# Test Caddy configuration
sudo caddy validate --config /etc/caddy/Caddyfile
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Caddy configuration is valid.${RESET}"
else
    echo -e "${RED}Caddy configuration test failed. Please check the configuration.${RESET}"
    exit 1
fi

# Ensure Caddy starts on boot and start Caddy
sudo systemctl enable caddy
sudo systemctl start caddy
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Caddy is now running and enabled to start on boot.${RESET}"
else
    echo -e "${RED}Failed to start Caddy.${RESET}"
    exit 1
fi

# Check if Caddy is active and enabled
if systemctl is-active --quiet caddy; then
    echo -e "${GREEN}Caddy is active.${RESET}"
else
    echo -e "${RED}Caddy is not running.${RESET}"
fi

if systemctl is-enabled --quiet caddy; then
    echo -e "${GREEN}Caddy is enabled to start on boot.${RESET}"
else
    echo -e "${RED}Caddy is not enabled to start on boot.${RESET}"
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
  echo "User '$MARIADB_DB_USER' already exists. Verifying password..."
  # Try to connect with the provided credentials
  if ! mysql -u"$MARIADB_DB_USER" -p"$MARIADB_DB_USER_PASSWORD" -e "SELECT 1;" >/dev/null 2>&1; then
    echo -e "${RED}Error: Password verification failed for user '$MARIADB_DB_USER'.${RESET}"
    echo ""
    echo "Would you like to reset the password?"
    echo -e "  ${GREEN}y${RESET} - Yes, generate a new random password"
    echo -e "  ${GREEN}n${RESET} - No, keep current password (installation will stop)"
    echo -n "Choice (y/n): "
    read RESET_PASSWORD

    if [ "$RESET_PASSWORD" = "y" ] || [ "$RESET_PASSWORD" = "Y" ]; then
      DB_PASSWORD=$(openssl rand -base64 15 | tr -d "=+/" | cut -c1-15)
      DB_PASSWORD_ESCAPED=$(printf '%s\n' "$DB_PASSWORD" | sed 's/[\/&]/\\&/g')
      sed -i "s/^MARIADB_DB_USER_PASSWORD=.*/MARIADB_DB_USER_PASSWORD=\"$DB_PASSWORD_ESCAPED\"/" user_config/settings
      mysql -e "ALTER USER '$MARIADB_DB_USER'@'%' IDENTIFIED BY '$DB_PASSWORD';"
      mysql -e "FLUSH PRIVILEGES;"
      echo -e "${GREEN}Password has been reset successfully.${RESET}"
      echo "New password has been saved to user_config/settings"
    else
      echo -e "${RED}Password verification failed and password was not reset.${RESET}"
      echo "Please set the correct password in user_config/settings and run this installation again."
      echo ""
      exit 1
    fi
  fi
  echo -e "${GREEN}Password verification successful.${RESET}"
else
  echo "User '$MARIADB_DB_USER' does not exist."
  mysql -e "CREATE USER IF NOT EXISTS '$MARIADB_DB_USER'@'%' IDENTIFIED BY '$MARIADB_DB_USER_PASSWORD';"
  mysql -e "GRANT ALL PRIVILEGES ON $MARIADB_DB_NAME.* TO '$MARIADB_DB_USER'@'%';"
  mysql -e "FLUSH PRIVILEGES;"
  echo -e "${GREEN}In mariadb/mysql, created the user ${MARIADB_DB_USER} and granted the user full access to the database ${MARIADB_DB_NAME}."
fi

# Configure MySQL connection limits and timeouts
echo "Configuring MySQL connection limits and timeouts..."

# Check if the MySQL configuration file already exists and has our settings
MYSQL_CONF_FILE="/etc/mysql/conf.d/mysql.cnf"
NEEDS_CONFIG=false

if [ ! -f "$MYSQL_CONF_FILE" ]; then
    echo "MySQL configuration file does not exist. Creating..."
    NEEDS_CONFIG=true
else
    # Check if our specific configurations are already present
    if ! grep -q "wait_timeout=240" "$MYSQL_CONF_FILE" || ! grep -q "max_connections=2000" "$MYSQL_CONF_FILE"; then
        echo "MySQL configuration file exists but missing required settings. Updating..."
        NEEDS_CONFIG=true
    else
        echo -e "${GREEN}MySQL configuration file already contains required settings.${RESET}"
    fi
fi

if [ "$NEEDS_CONFIG" = true ]; then
    # Create or update the configuration file with proper permissions
    sudo tee "$MYSQL_CONF_FILE" > /dev/null <<EOF
[mysqld]
wait_timeout=240
max_connections=2000
EOF

    # Set proper ownership and permissions
    sudo chown root:root "$MYSQL_CONF_FILE"
    sudo chmod 644 "$MYSQL_CONF_FILE"

    echo -e "${GREEN}MySQL connection settings configured in $MYSQL_CONF_FILE${RESET}"
    
    # Restart MariaDB to apply new configuration
    sudo systemctl restart mariadb
    echo -e "${GREEN}MariaDB restarted to apply configuration changes.${RESET}"
else
    echo -e "${GREEN}MySQL configuration is already up to date.${RESET}"
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