#!/bin/bash

######
# This script is used to merge settings from the user_config/settings file to
# user_config/frontend_settings.js and user_config/backend_settings.json files.
######

CURRENT_DIR=$(pwd)

# Load settings
source "$CURRENT_DIR/user_config/settings"

# Function to escape special characters in a variable for use with sed
escape_sed() {
    echo "$1" | sed 's/[\/&]/\\&/g'
}

# Function to perform sed operation
perform_sed() {
    local file=$1
    local search=$2
    local replace=$3
    if sed --version >/dev/null 2>&1; then
        # GNU sed
        sed -i -e "$search" "$file"
    else
        # BSD sed (macOS)
        sed -i '' -e "$search" "$file"
    fi
}

# Server URL
ESC_SERV_URL=$(escape_sed "$SERVER_WEB_ADDRESS")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"url\": \).*/\1\"$ESC_SERV_URL\",/"

# Server IP
ESC_SERV_IP=$(escape_sed "$SERVER_IP_ADDRESS")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"serverIp\": \).*/\1\"$ESC_SERV_IP\",/"

# Reservation min duration
MIN_DUR=$(escape_sed "$RESERVATION_MIN_DURATION")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"minimumDuration\": \).*/\1$MIN_DUR,/"

# Reservation max duration
MAX_DUR=$(escape_sed "$RESERVATION_MAX_DURATION")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"maximumDuration\": \).*/\1$MAX_DUR/"

# Reservation port start
RES_PORT_START=$(escape_sed "$DOCKER_RESERVATION_PORT_RANGE_START")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"port_range_start\": \).*/\1$RES_PORT_START,/"

# Reservation port end
RES_PORT_END=$(escape_sed "$DOCKER_RESERVATION_PORT_RANGE_END")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"port_range_end\": \).*/\1$RES_PORT_END,/"

# Timezone
ESCAPED_TIMEZONE=$(escape_sed "$TIMEZONE")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"timezone\": \).*/\1\"$ESCAPED_TIMEZONE\",/"
perform_sed user_config/frontend_settings.js "s/^\([[:space:]]*timezone: \).*/\1\"$ESCAPED_TIMEZONE\",/"

# Docker server name
ESC_SERV_NAME=$(escape_sed "$DOCKER_SERVER_NAME")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"serverName\": \).*/\1\"$ESC_SERV_NAME\",/"

# Docker mount location
ESC_MOUNT_LOCATION=$(escape_sed "$DOCKER_USER_MOUNT_LOCATION")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"userMountLocation\": \).*/\1\"$ESC_MOUNT_LOCATION\",/"

# Docker mount user
ESC_MOUNT_USER=$(escape_sed "$DOCKER_MOUNT_USER")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"mountUser\": \).*/\1\"$ESC_MOUNT_USER\",/"

# Docker mount group
ESC_MOUNT_GROUP=$(escape_sed "$DOCKER_MOUNT_GROUP")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"mountGroup\": \).*/\1\"$ESC_MOUNT_GROUP\",/"

# Docker Registry Address
ESCAPED_REGISTRY_ADDRESS=$(escape_sed "$DOCKER_REGISTRY_ADDRESS")
ESCAPED_REGISTRY_PORT=$(escape_sed "$DOCKER_REGISTRY_PORT")
ESCAPED_REGISTRY_FULL="${ESCAPED_REGISTRY_ADDRESS}:${ESCAPED_REGISTRY_PORT}"
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"registryAddress\": \).*/\1\"$ESCAPED_REGISTRY_FULL\",/"

# Server address in frontend settings file
# This is the backend API server address that the frontend connects to.
ESCAPED_SERVER_WEB_ADDRESS=$(escape_sed "$SERVER_WEB_ADDRESS")
ESCAPED_BACKEND_ADDITIONAL_PORT=$(escape_sed "$BACKEND_ADDITIONAL_PORT")
# If backend additional port was set, then prepend it with :
if [ -n "$ESCAPED_BACKEND_ADDITIONAL_PORT" ]; then
  ESCAPED_BACKEND_ADDITIONAL_PORT=":$ESCAPED_BACKEND_ADDITIONAL_PORT"
fi
perform_sed user_config/frontend_settings.js "s/^\([[:space:]]*baseAddress: \).*/\1\"$ESCAPED_SERVER_WEB_ADDRESS$ESCAPED_BACKEND_ADDITIONAL_PORT\/api\/\",/"

# App name
ESCAPED_APP_NAME=$(escape_sed "$APP_NAME")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"name\": \).*/\1\"$ESCAPED_APP_NAME\",/"
perform_sed user_config/frontend_settings.js "s/^\([[:space:]]*appName: \).*/\1\"$ESCAPED_APP_NAME\",/"

# Email address
ESCAPED_EMAIL_ADDRESS=$(escape_sed "$CONTACT_EMAIL")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"helpEmailAddress\": \).*/\1\"$ESCAPED_EMAIL_ADDRESS\"/"
perform_sed user_config/frontend_settings.js "s/^\([[:space:]]*contactEmail: \).*/\1\"$ESCAPED_EMAIL_ADDRESS\",/"

# Database URI
URI="mysql+pymysql://"$MARIADB_DB_USER":"$MARIADB_DB_USER_PASSWORD"@"$MARIADB_SERVER_ADDRESS"/"$MARIADB_DB_NAME
ESCAPED_URI=$(escape_sed "$URI")
perform_sed user_config/backend_settings.json "s/^\([[:space:]]*\"engineUri\": \).*/\1\"$ESCAPED_URI\",/"