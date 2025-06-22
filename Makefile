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
		echo "  $(GREEN)1$(RESET) - Continue with current settings"; \
		echo "  $(GREEN)2$(RESET) - Reconfigure mandatory settings"; \
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
		echo "$(GREEN)$(BOLD)Enable Automatic HTTPS with Let's Encrypt for Web Interface?$(RESET)"; \
		echo "Choose 'y' if you have a real domain name that resolves to this server."; \
		echo "Choose 'n' if you specified an IP address in the step above or do not want to setup ssl/https."; \
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
			sed -i "s/MARIADB_DB_USER_PASSWORD=\"password\"/MARIADB_DB_USER_PASSWORD=\"$$DB_PASSWORD\"/" user_config/settings; \
		else \
			sed -i "s/SERVER_IP_ADDRESS=\"[^\"]*\"/SERVER_IP_ADDRESS=\"$$SERVER_IP\"/" user_config/settings; \
			sed -i "s/MAIN_SERVER_WEB_HOST=\"[^\"]*\"/MAIN_SERVER_WEB_HOST=\"$$WEB_HOST\"/" user_config/settings; \
			sed -i "s/MAIN_SERVER_WEB_HTTPS=[^[:space:]]*/MAIN_SERVER_WEB_HTTPS=$$ENABLE_HTTPS/" user_config/settings; \
			ESCAPED_TIMEZONE=$$(echo "$$TIMEZONE_INPUT" | sed 's/\//\\\//g'); \
			sed -i "s/TIMEZONE=\"[^\"]*\"/TIMEZONE=\"$$ESCAPED_TIMEZONE\"/" user_config/settings; \
			sed -i "s/RESERVATION_MIN_DURATION=[^[:space:]]*/RESERVATION_MIN_DURATION=$$MIN_DURATION/" user_config/settings; \
			sed -i "s/RESERVATION_MAX_DURATION=[^[:space:]]*/RESERVATION_MAX_DURATION=$$MAX_DURATION/" user_config/settings; \
		fi; \
		chown $${SUDO_USER:-$(shell whoami)}:$${SUDO_USER:-$(shell whoami)} user_config/settings 2>/dev/null || true; \
		\
		echo ""; \
		echo "$(GREEN)$(BOLD)Great! Your mandatory configurations have been setup successfully!$(RESET)"; \
		echo ""; \
		echo "$(BOLD)Configuration Summary:$(RESET)"; \
		echo "  - Server IP: $(GREEN)$$SERVER_IP$(RESET)"; \
		echo "  - Web Host: $(GREEN)$$WEB_HOST$(RESET)"; \
		if [ "$$ENABLE_HTTPS" = "true" ]; then \
			echo "  - Web Address: $(GREEN)https://$$WEB_HOST$(RESET)"; \
		else \
			echo "  - Web Address: $(GREEN)http://$$WEB_HOST$(RESET)"; \
		fi; \
		echo "  - Timezone: $(GREEN)$$TIMEZONE_INPUT$(RESET)"; \
		echo "  - Reservation Duration: $(GREEN)$$MIN_DURATION - $$MAX_DURATION hours$(RESET)"; \
		echo ""; \
		echo "$(GREEN)$(BOLD)Next steps:$(RESET)"; \
		echo "$(GREEN)1. Please review the $(BOLD)user_config/settings$(RESET)$(GREEN) file to verify your settings"; \
		echo "2. Run $(BOLD)sudo make setup-main-server$(RESET)$(GREEN) again and finish the installation"; \
		echo "\nNote: The error message below is expected and can be ignored.$(RESET)"; \
		touch .settings_just_created; \
		exit 1; \
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

setup-main-server: check-os-ubuntu interactive-settings-creation ## Installs and configures all dependencies for main server. Only works on Ubuntu 24.04. If using any other operating system, then refer to the readme documentation for manual steps. Call 'make start-main-server' after setup.
	@if [ -f .settings_just_created ]; then \
		rm -f .settings_just_created; \
		exit 0; \
	fi
	@chmod +x scripts/install_webserver_dependencies.bash
	@./scripts/install_webserver_dependencies.bash
	sudo -u $${SUDO_USER:-$(shell whoami)} $(PIP) install -r webapp/backend/requirements.txt --break-system-packages --ignore-installed
	# Fix ownership of frontend directory first to avoid permission issues
	@chown -R $${SUDO_USER:-$(shell whoami)}:$${SUDO_USER:-$(shell whoami)} webapp/frontend/ 2>/dev/null || true
	# Install frontend dependencies as the original user
	cd webapp/frontend && sudo -u $${SUDO_USER:-$(shell whoami)} npm install

	@echo "\n$(GREEN)The main server has been setup.\n"
	@echo "NEXT STEPS:"
	@echo "1. Run command $(BOLD)pm2 startup$(RESET)$(GREEN) and copy/paste the command that is outputted to your terminal."
	@echo "2. Restart the machine for all the changes to take effect."
	@echo "3. Run $(BOLD)make start-main-server$(RESET)$(GREEN) to start the main server.$(RESET)\n"

start-main-server: verify-config-file-exists apply-settings ## Starts all the main server services or restarts them if started. Caddy is used to create a reverse proxy with automatic HTTPS. pm2 process manager is used to run the frontend and backend.
	@sudo cp user_config/Caddyfile /etc/caddy/Caddyfile
	@sudo systemctl reload caddy
	@cd webapp/frontend && pm2 restart frontend 2>/dev/null || pm2 start "npm run production" --name frontend --log-date-format="YYYY-MM-DD HH:mm Z"
	@cd webapp/backend && pm2 restart backend 2>/dev/null || pm2 start "$(PYTHON) main.py" --name backend --log-date-format="YYYY-MM-DD HH:mm Z"
	@pm2 save
	@URL=$$(grep '"url"' webapp/backend/settings.json | sed 's/.*"url": "\(.*\)".*/\1/') && \
	echo "" && \
	echo "$(GREEN)Web servers (nginx proxy, frontend, backend) have been started / restarted!$(RESET)" && \
	echo "Access the launched web interface at: $(GREEN)$$URL$(RESET) (it can take several seconds for the server to launch)" && \
	echo "You can view any logs (errors) using the $(GREEN)make logs$(RESET) command."

setup-docker-utility: verify-config-file-exists apply-settings ## Setups the Docker utility. The Docker utility will start, stop, and restart the containers on this machine. Call 'make start-docker-utility' after setup.
	@chmod +x scripts/install_docker_dependencies.bash
	@./scripts/install_docker_dependencies.bash
	sudo -u $${SUDO_USER:-$(shell whoami)} $(PIP) install -r webapp/backend/requirements.txt --break-system-packages --ignore-installed
	@usermod -aG docker $${SUDO_USER:-$(shell whoami)}
	@echo "\n$(GREEN)The Docker utility has been setup.\n"
	@echo "NEXT STEPS:"
	@echo "1. Run command $(BOLD)pm2 startup$(RESET)$(GREEN) and copy/paste the command to your terminal."
	@echo "2. Restart the machine for all the changes to take effect.$(RESET)\n"

start-docker-utility: apply-settings ## Starts the Docker utility. The utility starts, stops, restarts reserved containers on this server. pm2 process manager is used to run the script in the background.
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