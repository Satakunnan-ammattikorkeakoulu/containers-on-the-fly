PYTHON=python3
PIP=pip

# Define variables
BACKEND_PATH = webapp/backend
BACKEND_SRC = main.py
FOLDER_SRC=src
APP_ENTRYPOINT=$(FOLDER_SRC)/main.py
CONFIG_SETTINGS = "user_config/settings"

GREEN=\033[0;32m
BOLD=\033[1m
RED=\033[0;31m
RESET=\033[0m



help:
	$(info Make tool for the containers on the fly project.)
	$(info Using this make tool, you can setup and run the services. Commands available:)
	$(info )
	@grep '^[[:alnum:]_-]*:.* ##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS=":.* ## "}; {printf "> make %-25s\n%s\n\n", $$1, $$2};'

# Helper targets

apply-firewall-rules: # Applies ufw firewall rules to the server
	@chmod +x scripts/apply_firewall_rules.bash
	@./scripts/apply_firewall_rules.bash

interactive-settings-creation: # Creates settings file interactively if it doesn't exist or prompts for continuation if it exists
	@if [ ! -e $(CONFIG_SETTINGS) ]; then \
		RECONFIGURE_SETTINGS=true; \
		FIRST_TIME_SETUP=true; \
	else \
		EXISTING_SERVER_IP=$$(grep "^SERVER_IP_ADDRESS=" user_config/settings | cut -d'"' -f2); \
		EXISTING_WEB_HOST=$$(grep "^MAIN_SERVER_WEB_HOST=" user_config/settings | cut -d'"' -f2); \
		EXISTING_WEB_HTTPS=$$(grep "^MAIN_SERVER_WEB_HTTPS=" user_config/settings | cut -d'=' -f2); \
		EXISTING_TIMEZONE=$$(grep "^TIMEZONE=" user_config/settings | cut -d'"' -f2); \
		EXISTING_MIN_DURATION=$$(grep "^RESERVATION_MIN_DURATION=" user_config/settings | cut -d'=' -f2); \
		EXISTING_MAX_DURATION=$$(grep "^RESERVATION_MAX_DURATION=" user_config/settings | cut -d'=' -f2); \
		\
		if [ "$$EXISTING_WEB_HTTPS" = "true" ]; then \
			EXISTING_WEB_ADDRESS="https://$$EXISTING_WEB_HOST"; \
		else \
			EXISTING_WEB_ADDRESS="http://$$EXISTING_WEB_HOST"; \
		fi; \
		\
		echo "$(GREEN)Settings file exists with current configuration:$(RESET)"; \
		echo "  - Server IP: $(GREEN)$$EXISTING_SERVER_IP$(RESET)"; \
		echo "  - Web Host: $(GREEN)$$EXISTING_WEB_HOST$(RESET)"; \
		echo "  - Web Address: $(GREEN)$$EXISTING_WEB_ADDRESS$(RESET)"; \
		echo "  - Timezone: $(GREEN)$$EXISTING_TIMEZONE$(RESET)"; \
		echo "  - Reservation Duration: $(GREEN)$$EXISTING_MIN_DURATION - $$EXISTING_MAX_DURATION hours$(RESET)"; \
		echo ""; \
		echo "What would you like to do?"; \
		echo "  $(GREEN)1$(RESET) - Use these settings and start main server setup"; \
		echo "  $(GREEN)2$(RESET) - Reconfigure main server settings"; \
		echo "  $(GREEN)3$(RESET) - Cancel setup"; \
		echo -n "Enter your choice (1, 2, or 3): "; \
		read SETUP_CHOICE; \
		\
		case "$$SETUP_CHOICE" in \
			1) \
				echo "Continuing with existing settings..."; \
				RECONFIGURE_SETTINGS=false; \
				FIRST_TIME_SETUP=false; \
				;; \
			2) \
				echo "Reconfiguring settings..."; \
				RECONFIGURE_SETTINGS=true; \
				FIRST_TIME_SETUP=false; \
				;; \
			3) \
				echo "Setup cancelled."; \
				exit 1; \
				;; \
			*) \
				echo "$(RED)Invalid choice. Setup cancelled.$(RESET)"; \
				exit 1; \
				;; \
		esac; \
	fi; \
	\
	if [ "$$RECONFIGURE_SETTINGS" = "true" ]; then \
		echo ""; \
		echo "$(GREEN)$(BOLD)Welcome to Containers on the Fly Main Server Setup!$(RESET)"; \
		echo "We're starting the installation process for your main server."; \
		echo "Since this is your first time running the setup, we'll ask you for some"; \
		echo "mandatory configuration settings to get your server up and running."; \
		echo ""; \
		\
		echo "Detecting IP addresses..."; \
		LOCAL_IP=$$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' || echo ""); \
		INTERNET_IP=$$(timeout 10 curl -s ifconfig.me 2>/dev/null || timeout 10 curl -s ipinfo.io/ip 2>/dev/null || echo ""); \
		\
		echo ""; \
		echo "$(GREEN)$(BOLD)Server IP Address:$(RESET)"; \
		if [ -n "$$LOCAL_IP" ]; then \
			echo "  $(GREEN)1$(RESET) - Local IP address: $(GREEN)$$LOCAL_IP$(RESET)"; \
		fi; \
		if [ -n "$$INTERNET_IP" ]; then \
			echo "  $(GREEN)2$(RESET) - Internet-facing IP address: $(GREEN)$$INTERNET_IP$(RESET)"; \
		fi; \
		echo "  $(GREEN)3$(RESET) - Manually enter IP address"; \
		echo ""; \
		echo -n "Enter your choice (1, 2, or 3): "; \
		read IP_CHOICE; \
		\
		case "$$IP_CHOICE" in \
			1) \
				if [ -n "$$LOCAL_IP" ]; then \
					SERVER_IP=$$LOCAL_IP; \
					echo "Using local IP address: $(GREEN)$$SERVER_IP$(RESET)"; \
				else \
					echo "$(RED)Local IP could not be determined. Please enter manually:$(RESET)"; \
					echo -n "IP address: "; \
					read SERVER_IP; \
				fi \
				;; \
			2) \
				if [ -n "$$INTERNET_IP" ]; then \
					SERVER_IP=$$INTERNET_IP; \
					echo "Using internet-facing IP address: $(GREEN)$$SERVER_IP$(RESET)"; \
				else \
					echo "$(RED)Internet-facing IP could not be determined. Please enter manually:$(RESET)"; \
					echo -n "IP address: "; \
					read SERVER_IP; \
				fi \
				;; \
			3) \
				echo -n "Please enter the IP address manually: "; \
				read SERVER_IP; \
				;; \
			*) \
				echo "$(RED)Invalid choice. Please enter manually:$(RESET)"; \
				echo -n "IP address: "; \
				read SERVER_IP; \
				;; \
		esac; \
		\
		echo ""; \
		echo "$(GREEN)$(BOLD)Web Server Host:$(RESET)"; \
		echo "Domain name or IP address, without http/https."; \
		echo "This will be used to access your web interface."; \
		echo "Examples: \"mydomain.com\", \"localhost\", \"$$SERVER_IP\""; \
		echo ""; \
		echo -n "Enter web server host (or empty for $(GREEN)$$SERVER_IP$(RESET)): "; \
		read WEB_HOST; \
		if [ -z "$$WEB_HOST" ]; then \
			WEB_HOST=$$SERVER_IP; \
		fi; \
		\
		echo ""; \
		echo "$(GREEN)$(BOLD)Enable HTTPS for Web Interface?$(RESET)"; \
		echo "By default, HTTPS uses Let's Encrypt for automatic certificate management."; \
		echo "You can also configure custom SSL certificates in the settings file if needed."; \
		echo ""; \
		echo "Choose 'y' if you have a real domain name that resolves to this server."; \
		echo "Choose 'n' if you specified an IP address in the step above or do not want HTTPS."; \
		echo -n "Enable HTTPS? (y/n) (or empty for $(GREEN)n$(RESET)): "; \
		read HTTPS_CHOICE; \
		if [ "$$HTTPS_CHOICE" = "y" ] || [ "$$HTTPS_CHOICE" = "Y" ]; then \
			ENABLE_HTTPS="true"; \
		else \
			ENABLE_HTTPS="false"; \
		fi; \
		\
		echo ""; \
		echo "$(GREEN)$(BOLD)Server Timezone:$(RESET)"; \
		echo "Enter your server's timezone for proper scheduling and logging."; \
		echo "Common examples: Europe/London, America/New_York, Asia/Tokyo, UTC"; \
		echo "Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"; \
		echo -n "Enter timezone (or empty for $(GREEN)Europe/Helsinki$(RESET)): "; \
		read TIMEZONE_INPUT; \
		if [ -z "$$TIMEZONE_INPUT" ]; then \
			TIMEZONE_INPUT="Europe/Helsinki"; \
		fi; \
		\
		echo ""; \
		echo "$(GREEN)$(BOLD)Container Reservation Duration:$(RESET)"; \
		echo "Set the minimum and maximum duration (hours) users can reserve containers."; \
		echo "This can prevent super short bookings and stops people from reserving containers forever."; \
		echo ""; \
		echo -n "Minimum reservation duration in hours (or empty for $(GREEN)5$(RESET)): "; \
		read MIN_DURATION; \
		if [ -z "$$MIN_DURATION" ]; then \
			MIN_DURATION="5"; \
		fi; \
		echo -n "Maximum reservation duration in hours (or empty for $(GREEN)72$(RESET)): "; \
		read MAX_DURATION; \
		if [ -z "$$MAX_DURATION" ]; then \
			MAX_DURATION="72"; \
		fi; \
		\
		if [ "$$FIRST_TIME_SETUP" = "true" ]; then \
			DB_PASSWORD=$$(openssl rand -base64 15 | tr -d "=+/" | cut -c1-15); \
			cp user_config/settings_example user_config/settings; \
			sed -i "s/SERVER_IP_ADDRESS=\"YOUR_IP_HERE\"/SERVER_IP_ADDRESS=\"$$SERVER_IP\"/" user_config/settings; \
			sed -i "s/MAIN_SERVER_WEB_HOST=\"YOUR_IP_OR_DOMAIN_HERE\"/MAIN_SERVER_WEB_HOST=\"$$WEB_HOST\"/" user_config/settings; \
			sed -i "s/MAIN_SERVER_WEB_HTTPS=false/MAIN_SERVER_WEB_HTTPS=$$ENABLE_HTTPS/" user_config/settings; \
			sed -i "s/TIMEZONE=\"Europe\/Helsinki\"/TIMEZONE=\"$$TIMEZONE_INPUT\"/" user_config/settings; \
			sed -i "s/RESERVATION_MIN_DURATION=5/RESERVATION_MIN_DURATION=$$MIN_DURATION/" user_config/settings; \
			sed -i "s/RESERVATION_MAX_DURATION=72/RESERVATION_MAX_DURATION=$$MAX_DURATION/" user_config/settings; \
			DB_PASSWORD_ESCAPED=$$(printf '%s\n' "$$DB_PASSWORD" | sed 's/[\/&]/\\&/g'); \
			sed -i "s/^MARIADB_DB_USER_PASSWORD=.*/MARIADB_DB_USER_PASSWORD=\"$$DB_PASSWORD_ESCAPED\"/" user_config/settings; \
		else \
			sed -i "s/SERVER_IP_ADDRESS=\"[^\"]*\"/SERVER_IP_ADDRESS=\"$$SERVER_IP\"/" user_config/settings; \
			sed -i "s/MAIN_SERVER_WEB_HOST=\"[^\"]*\"/MAIN_SERVER_WEB_HOST=\"$$WEB_HOST\"/" user_config/settings; \
			sed -i "s/MAIN_SERVER_WEB_HTTPS=[^[:space:]]*/MAIN_SERVER_WEB_HTTPS=$$ENABLE_HTTPS/" user_config/settings; \
			ESCAPED_TIMEZONE=$$(echo "$$TIMEZONE_INPUT" | sed 's/\//\\\//g'); \
			sed -i "s/TIMEZONE=\"[^\"]*\"/TIMEZONE=\"$$ESCAPED_TIMEZONE\"/" user_config/settings; \
			sed -i "s/RESERVATION_MIN_DURATION=[^[:space:]]*/RESERVATION_MIN_DURATION=$$MIN_DURATION/" user_config/settings; \
			sed -i "s/RESERVATION_MAX_DURATION=[^[:space:]]*/RESERVATION_MAX_DURATION=$$MAX_DURATION/" user_config/settings; \
			DB_PASSWORD_ESCAPED=$$(printf '%s\n' "$$DB_PASSWORD" | sed 's/[\/&]/\\&/g'); \
			sed -i "s/^MARIADB_DB_USER_PASSWORD=.*/MARIADB_DB_USER_PASSWORD=\"$$DB_PASSWORD_ESCAPED\"/" user_config/settings; \
		fi; \
		chown $${SUDO_USER:-$(shell whoami)}:$${SUDO_USER:-$(shell whoami)} user_config/settings 2>/dev/null || true; \
		\
		echo ""; \
		echo "$(GREEN)$(BOLD)Great! Your main server configurations have been setup successfully!$(RESET)"; \
		echo ""; \
		echo "$(GREEN)$(BOLD)!! IMPORTANT !!$(RESET) Please take a moment to manually review the full $(GREEN)user_config/settings$(RESET) file"; \
		echo "as it contains additional optional settings that you may want to configure for your setup."; \
		echo ""; \
		echo -n "Press Enter to continue and please manually review the settings file before you proceed with the installation."; \
		read CONTINUE_INPUT; \
	fi; \
	\
	# Loop back to show updated configuration if settings were just changed \
	if [ "$$RECONFIGURE_SETTINGS" = "true" ]; then \
		echo "$(GREEN)Updated main server settings:$(RESET)"; \
		UPDATED_SERVER_IP=$$(grep "^SERVER_IP_ADDRESS=" user_config/settings | cut -d'"' -f2); \
		UPDATED_WEB_HOST=$$(grep "^MAIN_SERVER_WEB_HOST=" user_config/settings | cut -d'"' -f2); \
		UPDATED_WEB_HTTPS=$$(grep "^MAIN_SERVER_WEB_HTTPS=" user_config/settings | cut -d'=' -f2); \
		UPDATED_TIMEZONE=$$(grep "^TIMEZONE=" user_config/settings | cut -d'"' -f2); \
		UPDATED_MIN_DURATION=$$(grep "^RESERVATION_MIN_DURATION=" user_config/settings | cut -d'=' -f2); \
		UPDATED_MAX_DURATION=$$(grep "^RESERVATION_MAX_DURATION=" user_config/settings | cut -d'=' -f2); \
		\
		if [ "$$UPDATED_WEB_HTTPS" = "true" ]; then \
			UPDATED_WEB_ADDRESS="https://$$UPDATED_WEB_HOST"; \
		else \
			UPDATED_WEB_ADDRESS="http://$$UPDATED_WEB_HOST"; \
		fi; \
		\
		echo "  - Server IP: $(GREEN)$$UPDATED_SERVER_IP$(RESET)"; \
		echo "  - Web Host: $(GREEN)$$UPDATED_WEB_HOST$(RESET)"; \
		echo "  - Web Address: $(GREEN)$$UPDATED_WEB_ADDRESS$(RESET)"; \
		echo "  - Timezone: $(GREEN)$$UPDATED_TIMEZONE$(RESET)"; \
		echo "  - Reservation Duration: $(GREEN)$$UPDATED_MIN_DURATION - $$UPDATED_MAX_DURATION hours$(RESET)"; \
		echo ""; \
		echo "What would you like to do?"; \
		echo "  $(GREEN)1$(RESET) - Proceed with installation using these settings"; \
		echo "  $(GREEN)2$(RESET) - Reconfigure main server settings again"; \
		echo "  $(GREEN)3$(RESET) - Cancel setup"; \
		echo -n "Enter your choice (1, 2, or 3): "; \
		read FINAL_CHOICE; \
		\
		case "$$FINAL_CHOICE" in \
			1) \
				echo "Proceeding with main server installation..."; \
				;; \
			2) \
				echo "Starting reconfiguration again..."; \
				exec $(MAKE) interactive-settings-creation; \
				;; \
			3) \
				echo "Setup cancelled."; \
				exit 1; \
				;; \
			*) \
				echo "$(RED)Invalid choice. Setup cancelled.$(RESET)"; \
				exit 1; \
				;; \
		esac; \
	fi

verify-config-file-exists: # Verify that the main configuration file exists.
	@if [ ! -e $(CONFIG_SETTINGS) ]; then \
		echo "Error: $(CONFIG_SETTINGS) does not exist. Please copy user_config/settings_example to user_config/settings and configure it first."; \
		exit 1; \
	fi

check-os-ubuntu: # Checks if the operating system is Ubuntu 24.04. Stops executing if not.
	@OS_NAME=$$(lsb_release -si 2>/dev/null || echo "Unknown") && \
	OS_VERSION=$$(lsb_release -sr 2>/dev/null || echo "Unknown") && \
	if [ "$$OS_NAME" != "Ubuntu" ]; then \
		echo "\n$(RED)Error: This setup script is only compatible with Ubuntu Linux. Please refer to the readme documentation for manual steps. Exiting.$(RESET)"; \
		exit 1; \
	elif [ "$$OS_VERSION" != "24.04" ]; then \
		echo "\n$(RED)Error: This setup script is only compatible with Ubuntu 24.04. Current version: $$OS_VERSION. Please refer to the readme documentation for manual steps. Exiting.$(RESET)"; \
		exit 1; \
	fi
	@echo ""
	@echo "$(GREEN)Operating system is Ubuntu 24.04. Proceeding with setup.$(RESET)"

apply-settings: # Applies the settings from user_config/settings to template files and generates configuration files.
	@chmod +x scripts/apply_settings.py
	@$(PYTHON) scripts/apply_settings.py

# Production targets

setup-main-server: check-os-ubuntu interactive-settings-creation apply-settings ## Run this with sudo. Installs and configures all dependencies for main server. Call 'make start-main-server' after setup.
	@echo ""
	@echo "$(GREEN)$(BOLD)Firewall Configuration$(RESET)"
	@echo "$(GREEN)HIGHLY RECOMMENDED:$(RESET) Configure UFW firewall rules to secure your server."
	@echo "This will:"
	@echo "  - Enable UFW firewall with secure defaults"
	@echo "  - Allow SSH (22), HTTP (80), HTTPS (443)"
	@echo "  - Allow container ports (2000-3000 by default)"
	@echo "  - Secure Docker registry and containers"
	@echo ""
	@echo "$(RED)WARNING:$(RESET) This will $(RED)RESET$(RESET) any existing UFW firewall rules!"
	@echo ""
	@echo "Configure firewall rules automatically?"
	@echo "  $(GREEN)y$(RESET) - Yes, configure firewall rules (recommended)"
	@echo "  $(GREEN)n$(RESET) - No, skip firewall configuration (not recommended)"
	@echo -n "Choice (y/n): "; \
	read FIREWALL_CHOICE; \
	echo ""; \
	if [ "$$FIREWALL_CHOICE" = "y" ] || [ "$$FIREWALL_CHOICE" = "Y" ]; then \
		echo "$(GREEN)Configuring firewall rules...$(RESET)"; \
		$(MAKE) apply-firewall-rules; \
		echo "$(GREEN)Firewall configuration completed.$(RESET)"; \
	else \
		echo "$(RED)WARNING: Firewall not configured!$(RESET)"; \
		echo "Your server may be vulnerable to unauthorized access."; \
		echo "You can configure it later with: $(BOLD)make apply-firewall-rules$(RESET)"; \
		echo -n "Press Enter to continue with setup anyway..."; \
		read CONTINUE_ANYWAY; \
	fi; \
	echo ""
	@chmod +x scripts/install_webserver_dependencies.bash
	@./scripts/install_webserver_dependencies.bash
	sudo -u $${SUDO_USER:-$(shell whoami)} $(PIP) install -r webapp/backend/requirements.txt --break-system-packages --ignore-installed
	# Fix ownership of frontend directory first to avoid permission issues
	@chown -R $${SUDO_USER:-$(shell whoami)}:$${SUDO_USER:-$(shell whoami)} webapp/frontend/ 2>/dev/null || true
	# Install frontend dependencies as the original user
	cd webapp/frontend && sudo -u $${SUDO_USER:-$(shell whoami)} npm install

	# Automatically configure pm2 startup
	@echo "$(GREEN)Configuring pm2 startup...$(RESET)"
	@PM2_STARTUP_CMD=$$(sudo -u $${SUDO_USER:-$(shell whoami)} pm2 startup 2>/dev/null | grep "sudo env" || true); \
	if [ -n "$$PM2_STARTUP_CMD" ]; then \
		echo "Executing pm2 startup command automatically...$(RESET)"; \
		eval "$$PM2_STARTUP_CMD"; \
		echo "PM2 startup configured successfully.$(RESET)"; \
	else \
		echo "$(RED)Could not automatically configure pm2 startup. Please run 'pm2 startup' manually and run the output command at the end of the output.$(RESET)"; \
	fi

	@echo "\n$(GREEN)$(BOLD)The main server has been setup.$(RESET)\n"
	@echo "$(GREEN)$(BOLD)NEXT STEPS:$(RESET)"
	@echo "$(GREEN)* Run $(GREEN)$(BOLD)make start-main-server$(RESET)$(GREEN) to start the main server.$(RESET)\n"

start-main-server: verify-config-file-exists apply-settings ## Starts all the main server services or restarts them if started. Caddy is used to create a reverse proxy with automatic HTTPS. pm2 process manager is used to run the frontend and backend. Run this again after changing settings or pulling updates to restart the Docker utility and apply changes.
	@echo "Moving Caddyfile to /etc/caddy/Caddyfile"
	@sudo cp user_config/Caddyfile /etc/caddy/Caddyfile
	@echo "Reloading Caddy"
	@sudo systemctl reload caddy
	@echo "Starting frontend and backend"
	@cd webapp/frontend && pm2 restart frontend 2>/dev/null || pm2 start "npm run production" --name frontend --log-date-format="YYYY-MM-DD HH:mm Z"
	@cd webapp/backend && pm2 restart backend 2>/dev/null || pm2 start "$(PYTHON) main.py" --name backend --log-date-format="YYYY-MM-DD HH:mm Z"
	@pm2 save
	@URL=$$(grep -o '"url": "[^"]*"' webapp/backend/settings.json | cut -d'"' -f4) && \
	echo "" && \
	echo "$(GREEN)$(BOLD)Servers started/restarted!$(RESET)" && \
	echo "Access at: $(GREEN)$(BOLD)$$URL$(RESET) (can take some time for the server to start)" && \
	echo "View logs: $(GREEN)$(BOLD)make logs$(RESET)" && \
	echo "" && \
	echo "$(GREEN)Note:$(RESET) Run this task again after changing settings or pulling updates to restart servers and apply changes." && \
	echo "" && \
	echo "Potential Next Step:" && \
	echo "* If you have not yet setup the Docker utility, run $(GREEN)$(BOLD)sudo make setup-docker-utility$(RESET) to start setting it up.$(RESET)" && \
	echo ""

setup-docker-utility: check-os-ubuntu interactive-docker-settings-creation apply-settings ## Run this with sudo. Setups the Docker utility. The Docker utility will start, stop, and restart the containers on this machine. Call 'make start-docker-utility' after setup.
	@echo "Verifying Docker registry connectivity..."
	@REGISTRY_ADDRESS=$$(grep '"registryAddress"' webapp/backend/settings.json | sed 's/.*"registryAddress": "\(.*\)".*/\1/' 2>/dev/null) && \
	SERVER_IP=$$(grep '"serverIp"' webapp/backend/settings.json | sed 's/.*"serverIp": "\(.*\)".*/\1/' 2>/dev/null) && \
	if [ -z "$$SERVER_IP" ]; then \
		echo "$(RED)Error: serverIp not found in webapp/backend/settings.json$(RESET)"; \
		echo "$(RED)Make sure apply-settings has run successfully.$(RESET)"; \
		exit 1; \
	fi; \
	if [ -z "$$REGISTRY_ADDRESS" ]; then \
		echo "$(RED)Error: registryAddress not found in webapp/backend/settings.json$(RESET)"; \
		exit 1; \
	fi; \
	# Handle unsubstituted variables in registryAddress \
	if echo "$$REGISTRY_ADDRESS" | grep -q '\$$'; then \
		echo "Registry address contains unsubstituted variables: $$REGISTRY_ADDRESS"; \
		echo "Using serverIp ($$SERVER_IP) for registry connectivity test..."; \
		REGISTRY_IP="$$SERVER_IP"; \
		REGISTRY_PORT="5000"; \
	else \
		REGISTRY_IP=$$(echo "$$REGISTRY_ADDRESS" | sed 's/:.*//' 2>/dev/null); \
		REGISTRY_PORT=$$(echo "$$REGISTRY_ADDRESS" | sed 's/.*://' | sed 's/[^0-9]//g'); \
		if [ -z "$$REGISTRY_PORT" ]; then \
			REGISTRY_PORT="5000"; \
		fi; \
	fi; \
	if [ "$$REGISTRY_IP" = "$$SERVER_IP" ] || [ "$$REGISTRY_IP" = "localhost" ] || [ "$$REGISTRY_IP" = "127.0.0.1" ]; then \
		echo "Testing registry port accessibility on main server ($$REGISTRY_IP:$$REGISTRY_PORT)..."; \
		# Check if something is already running on the port \
		if timeout 2 bash -c "echo >/dev/tcp/$$REGISTRY_IP/$$REGISTRY_PORT" 2>/dev/null; then \
			echo "$(GREEN)Registry port is accessible and has a service already running.$(RESET)"; \
		else \
			echo "No service detected on port $$REGISTRY_PORT. Starting temporary test service..."; \
			# Start a simple HTTP server for testing port accessibility \
			$(PYTHON) -m http.server $$REGISTRY_PORT --bind 0.0.0.0 >/dev/null 2>&1 & \
			TEST_SERVICE_PID=$$!; \
			sleep 3; \
			# Test connection to our temporary HTTP server \
			if timeout 5 curl -s "http://$$REGISTRY_IP:$$REGISTRY_PORT" >/dev/null 2>&1; then \
				echo "$(GREEN)Registry port $$REGISTRY_PORT is accessible! Test successful.$(RESET)"; \
				TEST_RESULT="success"; \
			else \
				EXIT_CODE=$$?; \
				if [ $$EXIT_CODE -eq 124 ]; then \
					echo "\n$(RED)ERROR: Connection to registry port $$REGISTRY_PORT timed out.$(RESET)"; \
					echo "$(RED)This likely means the port is blocked by firewall or filtered.$(RESET)"; \
				else \
					echo "\n$(RED)ERROR: Cannot connect to registry port $$REGISTRY_PORT (connection refused).$(RESET)"; \
					echo "$(RED)This could mean the port is closed or blocked by firewall.$(RESET)"; \
				fi; \
				echo "$(RED)Please ensure:$(RESET)"; \
				echo "  - Port $$REGISTRY_PORT is open on this server"; \
				echo "  - Firewall rules allow access to port $$REGISTRY_PORT\n"; \
				TEST_RESULT="failed"; \
			fi; \
			# Stop the test service \
			kill $$TEST_SERVICE_PID 2>/dev/null || true; \
			wait $$TEST_SERVICE_PID 2>/dev/null || true; \
			echo "Temporary test service stopped."; \
			if [ "$$TEST_RESULT" = "failed" ]; then \
				exit 1; \
			fi; \
		fi; \
	else \
		echo "Testing connection to remote Docker registry at $$REGISTRY_IP:$$REGISTRY_PORT..."; \
		if ! timeout 10 nc -z $$REGISTRY_IP $$REGISTRY_PORT 2>/dev/null; then \
			echo ""; \
			echo "$(RED)ERROR: Cannot connect to Docker registry at $$REGISTRY_IP:$$REGISTRY_PORT$(RESET)"; \
			echo "$(RED)Please ensure:$(RESET)"; \
			echo "  - The main server is running and accessible"; \
			echo "  - Main server has allowed access using command $(BOLD)make allow-container-server IP=<IP_ADDRESS_OF_THIS_CONTAINER_SERVER>$(RESET)"; \
			echo "  - Port $$REGISTRY_PORT is open on the main server"; \
			echo "  - The Docker registry service is running on the main server\n"; \
			exit 1; \
		fi; \
		echo "$(GREEN)Docker registry connection successful.$(RESET)"; \
	fi
	@chmod +x scripts/install_docker_dependencies.bash
	@./scripts/install_docker_dependencies.bash
	sudo -u $${SUDO_USER:-$(shell whoami)} $(PIP) install -r webapp/backend/requirements.txt --break-system-packages --ignore-installed
	@usermod -aG docker $${SUDO_USER:-$(shell whoami)}

	# Automatically configure pm2 startup
	@echo "$(GREEN)Configuring pm2 startup...$(RESET)"
	@PM2_STARTUP_CMD=$$(sudo -u $${SUDO_USER:-$(shell whoami)} pm2 startup 2>/dev/null | grep "sudo env" || true); \
	if [ -n "$$PM2_STARTUP_CMD" ]; then \
		echo "Executing pm2 startup command automatically...$(RESET)"; \
		eval "$$PM2_STARTUP_CMD"; \
		echo "PM2 startup configured successfully.$(RESET)"; \
	else \
		echo "$(RED)Could not automatically configure pm2 startup. Please run 'pm2 startup' manually and run the output command at the end of the output.$(RESET)"; \
	fi

	@echo "\n$(GREEN)The Docker utility has been setup.\n"
	@echo "NEXT STEPS:"
	@echo "1. Restart the machine for all the changes to take effect."
	@echo "2. Run $(BOLD)make start-docker-utility$(RESET)$(GREEN) to start the Docker utility.$(RESET)\n"

start-docker-utility: apply-settings ## Starts the Docker utility. The utility starts, stops, restarts reserved containers on this server. pm2 process manager is used to run the script in the background. Run this again after changing settings or pulling updates to restart the Docker utility and apply changes.
	@echo "Verifying that connection to the database can be made using the webapp/backend/settings.json setting engineUri..."
	@CONNECTION_URI=$$(grep '"engineUri"' webapp/backend/settings.json | sed 's/.*"engineUri": "\(.*\)".*/\1/') && \
	CONNECTION_OK=$$($(PYTHON) scripts/verify_db_connection.py "$$CONNECTION_URI") && \
	if [ "$$CONNECTION_OK" = "CONNECTION_OK" ]; then \
		echo "Connection to the database was successful. Proceeding."; \
	else \
		echo "\n$(RED)Connection to the database could not be established. Please check that you have the webapp/backend/settings.json setting engineUri properly set and that connection to the database can be made (firewalls etc...).$(RESET)"; \
		exit 1; \
	fi
	@cd webapp/backend && pm2 restart backendDockerUtil 2>/dev/null || pm2 start "$(PYTHON) dockerUtil.py" --name backendDockerUtil --log-date-format="YYYY-MM-DD HH:mm Z"
	@pm2 save
	@echo "\n$(GREEN)Docker utility is now running.$(RESET)"
	@echo "Containers will now automatically start, stop, and restart on this server."
	@echo ""
	@echo "View logs: $(GREEN)$(BOLD)make logs$(RESET)"
	@echo ""
	@echo "$(GREEN)Note:$(RESET) Run this task again after changing settings or pulling updates to restart the Docker utility and apply changes."
	@echo ""

allow-container-server: check-os-ubuntu ## Allows an external given container server to access this main server. For example: make allow-container-server IP=62.151.151.151
	@if [ -z "$(IP)" ]; then \
		echo "No IP address provided. Usage: make allow-container-server IP=<IP_ADDRESS>"; \
		exit 1; \
	fi; \
	echo "Allowing container server with IP: $(IP)"; \
	# Check if the script is run as root; \
	if [ "$$(id -u)" -ne 0 ]; then \
		echo "This script must be run with sudo privileges. Please run this with sudo permissions. Exiting."; \
		exit 1; \
	fi; \
	echo "Running as root, proceeding with firewall configuration"; \
	sudo ufw route insert 1 allow from $(IP) to any port 5000
	sudo ufw insert 1 allow from $(IP)

logs: ## View log entries for started servers (pm2)
	pm2 logs --lines 10000

status: ## Views the status of the started servers (pm2)
	pm2 list

stop-servers: ## Kills (stops) the frontend, backend and docker utility servers (pm2 process manager)
	@-pm2 delete frontend 2>/dev/null || echo "frontend pm2 service was not running. Nothing to stop."
	@-pm2 delete backend 2>/dev/null || echo "backend pm2 service was not running. Nothing to stop."
	@-pm2 delete backendDockerUtil 2>/dev/null || echo "backendDockerUtil pm2 service was not running. Nothing to stop."
	@echo "\n$(GREEN)Servers stopped!$(RESET)"


# Scripts for development

start-dev-frontend: apply-settings
	cd webapp/frontend && npm run serve

start-dev-backend: apply-settings
	cd webapp/backend && $(PYTHON) main.py

start-dev-docker-utility: apply-settings
	cd webapp/backend && $(PYTHON) dockerUtil.py

# Add this new target after the existing interactive-settings-creation target

interactive-docker-settings-creation: # Creates Docker utility settings interactively
	@if [ ! -e $(CONFIG_SETTINGS) ]; then \
		RECONFIGURE_SETTINGS=true; \
		FIRST_TIME_SETUP=true; \
	else \
		EXISTING_SERVER_IP=$$(grep "^SERVER_IP_ADDRESS=" user_config/settings | cut -d'"' -f2); \
		EXISTING_SERVER_NAME=$$(grep "^DOCKER_SERVER_NAME=" user_config/settings | cut -d'"' -f2); \
		EXISTING_PORT_START=$$(grep "^DOCKER_RESERVATION_PORT_RANGE_START=" user_config/settings | cut -d'=' -f2); \
		EXISTING_PORT_END=$$(grep "^DOCKER_RESERVATION_PORT_RANGE_END=" user_config/settings | cut -d'=' -f2); \
		EXISTING_REGISTRY_ADDRESS=$$(grep "^DOCKER_REGISTRY_ADDRESS=" user_config/settings | cut -d'=' -f2 | tr -d '"'); \
		# Show effective registry address (use SERVER_IP if registry address is empty) \
		if [ -z "$$EXISTING_REGISTRY_ADDRESS" ] || [ "$$EXISTING_REGISTRY_ADDRESS" = '""' ]; then \
			EFFECTIVE_REGISTRY_ADDRESS="$$EXISTING_SERVER_IP (default)"; \
		else \
			EFFECTIVE_REGISTRY_ADDRESS=$$EXISTING_REGISTRY_ADDRESS; \
		fi; \
		EXISTING_DB_ADDRESS=$$(grep "^MARIADB_SERVER_ADDRESS=" user_config/settings | cut -d'"' -f2); \
		EXISTING_DB_NAME=$$(grep "^MARIADB_DB_NAME=" user_config/settings | cut -d'"' -f2); \
		EXISTING_DB_USER=$$(grep "^MARIADB_DB_USER=" user_config/settings | cut -d'"' -f2); \
		\
		echo "$(GREEN)Docker settings file exists with current configuration:$(RESET)"; \
		echo "  - Current Server IP: $(GREEN)$$EXISTING_SERVER_IP$(RESET)"; \
		echo "  - Docker Server Name: $(GREEN)$$EXISTING_SERVER_NAME$(RESET)"; \
		echo "  - Port Range: $(GREEN)$$EXISTING_PORT_START - $$EXISTING_PORT_END$(RESET)"; \
		echo "  - Registry Address: $(GREEN)$$EFFECTIVE_REGISTRY_ADDRESS$(RESET)"; \
		echo "  - Registry Port: $(GREEN)5000$(RESET)"; \
		echo "  - Database Address: $(GREEN)$$EXISTING_DB_ADDRESS$(RESET)"; \
		echo "  - Database Name: $(GREEN)$$EXISTING_DB_NAME$(RESET)"; \
		echo "  - Database User: $(GREEN)$$EXISTING_DB_USER$(RESET)"; \
		echo ""; \
		echo "What would you like to do?"; \
		echo "  $(GREEN)1$(RESET) - Use these settings and start Docker utility setup"; \
		echo "  $(GREEN)2$(RESET) - Reconfigure Docker utility settings"; \
		echo "  $(GREEN)3$(RESET) - Cancel setup"; \
		echo -n "Enter your choice (1, 2, or 3): "; \
		read SETUP_CHOICE; \
		\
		case "$$SETUP_CHOICE" in \
			1) \
				echo "Continuing with existing settings..."; \
				RECONFIGURE_SETTINGS=false; \
				FIRST_TIME_SETUP=false; \
				;; \
			2) \
				echo "Reconfiguring settings..."; \
				RECONFIGURE_SETTINGS=true; \
				FIRST_TIME_SETUP=false; \
				;; \
			3) \
				echo "Setup cancelled."; \
				exit 1; \
				;; \
			*) \
				echo "$(RED)Invalid choice. Setup cancelled.$(RESET)"; \
				exit 1; \
				;; \
		esac; \
	fi; \
	\
	if [ "$$RECONFIGURE_SETTINGS" = "true" ]; then \
		echo ""; \
		echo "$(GREEN)$(BOLD)Welcome to Containers on the Fly Docker Utility Setup!$(RESET)"; \
		echo "We're starting the installation process for your Docker utility."; \
		echo ""; \
		\
		echo "$(GREEN)$(BOLD)Server Type Configuration:$(RESET)"; \
		echo "Are you setting up a Docker utility for:"; \
		echo "  $(GREEN)1$(RESET) - Main server (same machine as web interface)"; \
		echo "  $(GREEN)2$(RESET) - Separate container server (different machine)"; \
		echo -n "Enter your choice (1 or 2): "; \
		read SERVER_TYPE_CHOICE; \
		\
		case "$$SERVER_TYPE_CHOICE" in \
			1) \
				echo "Setting up Docker utility for main server..."; \
				IS_MAIN_SERVER=true; \
				DEFAULT_SERVER_NAME="server1"; \
				DB_ADDRESS="localhost"; \
				CURRENT_SERVER_IP=$$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' || echo "127.0.0.1"); \
				REGISTRY_ADDRESS=$$CURRENT_SERVER_IP; \
				SERVER_IP_ADDRESS=$$CURRENT_SERVER_IP; \
				DB_NAME="containerfly"; \
				DB_USER="containerflyuser"; \
				EXISTING_DB_PASSWORD=$$(grep "^MARIADB_DB_USER_PASSWORD=" user_config/settings | cut -d'"' -f2 2>/dev/null || echo ""); \
				if [ -z "$$EXISTING_DB_PASSWORD" ] || [ "$$EXISTING_DB_PASSWORD" = "password" ]; then \
					echo "$(GREEN)$(BOLD)Database Password:$(RESET)"; \
					echo "Enter database password for main server:"; \
					echo -n "Database password: "; \
					read DB_PASSWORD; \
				else \
					DB_PASSWORD=$$EXISTING_DB_PASSWORD; \
				fi \
				;; \
			2) \
				echo "Setting up Docker utility for separate container server..."; \
				IS_MAIN_SERVER=false; \
				DEFAULT_SERVER_NAME="server2"; \
				echo ""; \
				echo "$(GREEN)$(BOLD)Main Server IP Configuration:$(RESET)"; \
				echo -n "Enter the IP address of your main server: "; \
				read MAIN_SERVER_IP; \
				DB_ADDRESS=$$MAIN_SERVER_IP; \
				REGISTRY_ADDRESS=$$MAIN_SERVER_IP; \
				CURRENT_SERVER_IP=$$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' || echo "127.0.0.1"); \
				SERVER_IP_ADDRESS=$$CURRENT_SERVER_IP; \
				echo ""; \
				echo "$(GREEN)$(BOLD)Database Connection Details:$(RESET)"; \
				echo "These must match the database configuration on your main server."; \
				echo -n "Database name (or empty for $(GREEN)containerfly$(RESET)): "; \
				read DB_NAME; \
				if [ -z "$$DB_NAME" ]; then \
					DB_NAME="containerfly"; \
				fi; \
				echo -n "Database user (or empty for $(GREEN)containerflyuser$(RESET)): "; \
				read DB_USER; \
				if [ -z "$$DB_USER" ]; then \
					DB_USER="containerflyuser"; \
				fi; \
				echo "$(GREEN)$(BOLD)WARNING:$(RESET) Password will be visible on screen"; \
				echo -n "Database password: "; \
				read DB_PASSWORD \
				;; \
			*) \
				echo "$(RED)Invalid choice. Setup cancelled.$(RESET)"; \
				exit 1 \
				;; \
		esac; \
		\
		echo ""; \
		echo "$(GREEN)$(BOLD)Docker Server Name:$(RESET)"; \
		echo "This identifies your Docker server in the system."; \
		echo "Examples: \"server1\", \"server2\", \"docker-node-1\""; \
		echo -n "Enter Docker server name (or empty for $(GREEN)$$DEFAULT_SERVER_NAME$(RESET)): "; \
		read DOCKER_SERVER_NAME_INPUT; \
		if [ -z "$$DOCKER_SERVER_NAME_INPUT" ]; then \
			DOCKER_SERVER_NAME_INPUT=$$DEFAULT_SERVER_NAME; \
		fi; \
		\
		echo ""; \
		echo "$(GREEN)$(BOLD)Container Reservation Port Range:$(RESET)"; \
		echo "When containers are started, they're assigned ports from this range."; \
		echo "Make sure this range doesn't conflict with other services."; \
		echo -n "Port range start (or empty for $(GREEN)2000$(RESET)): "; \
		read PORT_START; \
		if [ -z "$$PORT_START" ]; then \
			PORT_START="2000"; \
		fi; \
		echo -n "Port range end (or empty for $(GREEN)3000$(RESET)): "; \
		read PORT_END; \
		if [ -z "$$PORT_END" ]; then \
			PORT_END="3000"; \
		fi; \
		\
		if [ "$$FIRST_TIME_SETUP" = "true" ]; then \
			cp user_config/settings_example user_config/settings; \
		fi; \
		\
		sed -i "s/SERVER_IP_ADDRESS=\"[^\"]*\"/SERVER_IP_ADDRESS=\"$$SERVER_IP_ADDRESS\"/" user_config/settings; \
		sed -i "s/DOCKER_SERVER_NAME=\"[^\"]*\"/DOCKER_SERVER_NAME=\"$$DOCKER_SERVER_NAME_INPUT\"/" user_config/settings; \
		sed -i "s/DOCKER_RESERVATION_PORT_RANGE_START=[^[:space:]]*/DOCKER_RESERVATION_PORT_RANGE_START=$$PORT_START/" user_config/settings; \
		sed -i "s/DOCKER_RESERVATION_PORT_RANGE_END=[^[:space:]]*/DOCKER_RESERVATION_PORT_RANGE_END=$$PORT_END/" user_config/settings; \
		sed -i "s/DOCKER_REGISTRY_ADDRESS=.*/DOCKER_REGISTRY_ADDRESS=$$REGISTRY_ADDRESS/" user_config/settings; \
		sed -i "s/MARIADB_SERVER_ADDRESS=\"[^\"]*\"/MARIADB_SERVER_ADDRESS=\"$$DB_ADDRESS\"/" user_config/settings; \
		sed -i "s/MARIADB_DB_NAME=\"[^\"]*\"/MARIADB_DB_NAME=\"$$DB_NAME\"/" user_config/settings; \
		sed -i "s/MARIADB_DB_USER=\"[^\"]*\"/MARIADB_DB_USER=\"$$DB_USER\"/" user_config/settings; \
		DB_PASSWORD_ESCAPED=$$(printf '%s\n' "$$DB_PASSWORD" | sed 's/[\/&]/\\&/g'); \
		sed -i "s/^MARIADB_DB_USER_PASSWORD=.*/MARIADB_DB_USER_PASSWORD=\"$$DB_PASSWORD_ESCAPED\"/" user_config/settings; \
		\
		chown $${SUDO_USER:-$(shell whoami)}:$${SUDO_USER:-$(shell whoami)} user_config/settings 2>/dev/null || true; \
		\
		echo ""; \
		echo "$(GREEN)$(BOLD)Great! Your Docker utility configurations have been setup successfully!$(RESET)"; \
		echo ""; \
		echo "$(GREEN)$(BOLD)!! IMPORTANT !!$(RESET) Please take a moment to manually review the full $(GREEN)user_config/settings$(RESET) file"; \
		echo "as it contains additional optional settings that you may want to configure for your setup."; \
		echo ""; \
		echo "What would you like to do?"; \
		echo "  $(GREEN)1$(RESET) - Proceed with Docker utility installation using these settings"; \
		echo "  $(GREEN)2$(RESET) - Reconfigure Docker utility settings again"; \
		echo "  $(GREEN)3$(RESET) - Cancel setup"; \
		echo -n "Enter your choice (1, 2, or 3): "; \
		read FINAL_CHOICE; \
		\
		case "$$FINAL_CHOICE" in \
			1) \
				echo "Proceeding with Docker utility installation..."; \
				;; \
			2) \
				echo "Starting reconfiguration again..."; \
				exec $(MAKE) interactive-docker-settings-creation; \
				;; \
			3) \
				echo "Setup cancelled."; \
				exit 1; \
				;; \
			*) \
				echo "$(RED)Invalid choice. Setup cancelled.$(RESET)"; \
				exit 1; \
				;; \
		esac; \
	fi