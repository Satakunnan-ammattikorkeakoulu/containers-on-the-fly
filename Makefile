PYTHON=python3
PIP=pip

# Define variables
BACKEND_PATH = webapp/backend
CONTAINER_SERVER_PATH = webapp/container_server
BACKEND_SRC = main.py
FOLDER_SRC=src
APP_ENTRYPOINT=$(FOLDER_SRC)/main.py
CONFIG_SETTINGS = "user_config/settings"

GREEN=\033[0;32m
BOLD=\033[1m
RED=\033[0;31m
RESET=\033[0m

.DEFAULT_GOAL = help

install-backend-deps: ## Install or update backend dependencies
	@echo ""
	@echo "Installing backend dependencies... (pip packages)"
	@sudo -u $${SUDO_USER:-$(shell whoami)} $(PIP) install -r webapp/backend/requirements.txt --break-system-packages --ignore-installed --no-warn-script-location -qq


help:
	$(info Make tool for the containers on the fly project.)
	$(info Using this make tool, you can setup and run the services. Commands available:)
	$(info )
	@grep '^[[:alnum:]_-]*:.* ##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS=":.* ## "}; {printf "> make %-25s\n%s\n\n", $$1, $$2};'

# Helper targets

apply-firewall-rules: # Applies iptables firewall rules to the server
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
		\
		# Reservation duration settings are now stored in the database \
		\
		if [ "$$FIRST_TIME_SETUP" = "true" ]; then \
			DB_PASSWORD=$$(openssl rand -base64 15 | tr -d "=+/" | cut -c1-15); \
			cp user_config/settings_example user_config/settings; \
			sed -i "s/SERVER_IP_ADDRESS=\"YOUR_IP_HERE\"/SERVER_IP_ADDRESS=\"$$SERVER_IP\"/" user_config/settings; \
			sed -i "s/MAIN_SERVER_WEB_HOST=\"YOUR_IP_OR_DOMAIN_HERE\"/MAIN_SERVER_WEB_HOST=\"$$WEB_HOST\"/" user_config/settings; \
			sed -i "s/MAIN_SERVER_WEB_HTTPS=false/MAIN_SERVER_WEB_HTTPS=$$ENABLE_HTTPS/" user_config/settings; \
			DB_PASSWORD_ESCAPED=$$(printf '%s\n' "$$DB_PASSWORD" | sed 's/[\/&]/\\&/g'); \
			sed -i "s/^MARIADB_DB_USER_PASSWORD=.*/MARIADB_DB_USER_PASSWORD=\"$$DB_PASSWORD_ESCAPED\"/" user_config/settings; \
		else \
			EXISTING_DB_PASSWORD=$$(grep "^MARIADB_DB_USER_PASSWORD=" user_config/settings | cut -d'"' -f2); \
			sed -i "s/SERVER_IP_ADDRESS=\"[^\"]*\"/SERVER_IP_ADDRESS=\"$$SERVER_IP\"/" user_config/settings; \
			sed -i "s/MAIN_SERVER_WEB_HOST=\"[^\"]*\"/MAIN_SERVER_WEB_HOST=\"$$WEB_HOST\"/" user_config/settings; \
			sed -i "s/MAIN_SERVER_WEB_HTTPS=[^[:space:]]*/MAIN_SERVER_WEB_HTTPS=$$ENABLE_HTTPS/" user_config/settings; \
			# Only update DB password if it's not already set \
			if [ -z "$$EXISTING_DB_PASSWORD" ]; then \
				DB_PASSWORD=$$(openssl rand -base64 15 | tr -d "=+/" | cut -c1-15); \
				DB_PASSWORD_ESCAPED=$$(printf '%s\n' "$$DB_PASSWORD" | sed 's/[\/&]/\\&/g'); \
				sed -i "s/^MARIADB_DB_USER_PASSWORD=.*/MARIADB_DB_USER_PASSWORD=\"$$DB_PASSWORD_ESCAPED\"/" user_config/settings; \
			fi; \
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

ensure-daemon-api-key: verify-config-file-exists # Ensures DAEMON_API_KEY exists and is populated in user_config/settings
	@if ! grep -q "^DAEMON_API_KEY=" user_config/settings; then \
		echo '' >> user_config/settings; \
		echo '' >> user_config/settings; \
		echo '# Shared secret (password) for main server web rest api <-> container server authentication.' >> user_config/settings; \
		echo '# This needs to be the same in your main server and in each (possible) separate container server' >> user_config/settings; \
		echo '# Auto-generated by setup-main-server to a random key if empty.' >> user_config/settings; \
		echo '# This cannot be empty and should be long and secure - Otherwise anyone could access your web server rest api!' >> user_config/settings; \
		echo 'DAEMON_API_KEY=""' >> user_config/settings; \
	fi
	@EXISTING_DAEMON_KEY=$$(grep "^DAEMON_API_KEY=" user_config/settings | cut -d'"' -f2); \
	if [ -z "$$EXISTING_DAEMON_KEY" ]; then \
		DAEMON_KEY=$$(openssl rand -base64 48 | tr -d "=+/" | cut -c1-48); \
		DAEMON_KEY_ESCAPED=$$(printf '%s\n' "$$DAEMON_KEY" | sed 's/[\/&]/\\&/g'); \
		sed -i "s/^DAEMON_API_KEY=.*/DAEMON_API_KEY=\"$$DAEMON_KEY_ESCAPED\"/" user_config/settings; \
		echo "Generated daemon API key."; \
	fi

apply-settings-main-server: ensure-daemon-api-key # Applies settings for main server context
	@chmod +x scripts/apply_settings.py
	@CONTAINERFLY_CONTEXT=main-server $(PYTHON) scripts/apply_settings.py

# Production targets

check-root: # Checks if running with root privileges
	@if [ "$$(id -u)" -ne 0 ]; then \
		echo "\n$(RED)Error: This command must be run with sudo privileges. Please run with sudo. Exiting.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Running with root privileges. Proceeding.$(RESET)"

check-not-root: # Checks if NOT running with root privileges
	@if [ "$$(id -u)" -eq 0 ]; then \
		echo "\n$(RED)Error: This command should NOT be run with sudo privileges. Please run without sudo. Exiting.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Running without root privileges. Proceeding.$(RESET)"

setup-main-server: check-root check-os-ubuntu interactive-settings-creation apply-settings-main-server ## Run this with sudo. Installs and configures all dependencies for main server. Call 'make start-main-server' after setup.
	@echo ""
	@echo "$(GREEN)$(BOLD)FIREWALL CONFIGURATION$(RESET)"
	@echo "$(GREEN)HIGHLY RECOMMENDED:$(RESET) Configure iptables firewall rules to secure your server."
	@echo "true" > /tmp/containerfly_server_type
	@echo "This will:"
	@echo "  - Enable iptables firewall with secure defaults"
	@echo "  - $(RED)BLOCK ALL incoming connections except:$(RESET)"
	@echo "    - SSH (22), HTTP (80), HTTPS (443)"
	@PORT_START=$$(grep "^DOCKER_RESERVATION_PORT_RANGE_START=" user_config/settings | cut -d'=' -f2 2>/dev/null || echo "2000"); \
	PORT_END=$$(grep "^DOCKER_RESERVATION_PORT_RANGE_END=" user_config/settings | cut -d'=' -f2 2>/dev/null || echo "3000"); \
	echo "    - Container ports ($$PORT_START-$$PORT_END)"; \
	ADDITIONAL_PORTS=$$(grep "^FIREWALL_ADDITIONAL_PORTS=" user_config/settings | cut -d'"' -f2 2>/dev/null || echo ""); \
	if [ -n "$$ADDITIONAL_PORTS" ]; then \
		echo "    - Additional ports ($$ADDITIONAL_PORTS)"; \
	fi; \
	echo "  - Secure Docker registry and containers"
	@echo ""
	@echo "$(RED)WARNING:$(RESET) This will $(RED)RESET$(RESET) any existing iptables firewall rules!"
	@echo ""
	@echo "Configure firewall rules automatically?"
	@echo "  $(GREEN)y$(RESET) - Yes, configure firewall rules (recommended)"
	@echo "  $(GREEN)n$(RESET) - No, skip firewall configuration (not recommended)"
	@echo "  NOTE: If you have already configured the firewall in the past, you can skip this step with option $(BOLD)n$(RESET)."
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
		echo "You can configure it later by running this command again."; \
		echo -n "Press Enter to continue with setup anyway..."; \
		read CONTINUE_ANYWAY; \
	fi; \
	echo ""
	@chmod +x scripts/install_webserver_dependencies.bash
	@./scripts/install_webserver_dependencies.bash
	@echo "$(GREEN)Installing frontend dependencies (clean install)...$(RESET)"
	cd webapp/frontend && sudo -u $${SUDO_USER:-$(shell whoami)} sh -c 'rm -rf package-lock.json && rm -rf node_modules || true && npm install'

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
	@echo "$(GREEN)1. Restart the machine for all changes to take effect.$(RESET)"
	@echo "$(GREEN)2. Run $(GREEN)$(BOLD)make start-main-server$(RESET)$(GREEN) to start the main server.$(RESET)\n"
	@rm -f .server_type

start-main-server: check-not-root verify-config-file-exists apply-settings-main-server init-database ## Starts all the main server services or restarts them if started. Caddy is used to create a reverse proxy with automatic HTTPS. pm2 process manager is used to run the frontend and backend. Run this again after changing settings to restart the Docker utility and apply changes.
	@echo ""
	@echo "Moving Caddyfile to /etc/caddy/Caddyfile"
	@sudo cp user_config/Caddyfile /etc/caddy/Caddyfile
	@echo "Reloading Caddy"
	@sudo systemctl reload caddy
	@echo ""
	@echo "Starting frontend and backend"
	@-pm2 delete frontend 2>/dev/null
	@if [ "$(DEV)" = "1" ]; then \
		echo "Starting frontend in development mode (Vite dev server)"; \
		cd webapp/frontend && pm2 start "npm run serve" --name frontend --log-date-format="YYYY-MM-DD HH:mm Z"; \
	else \
		echo "Building frontend for production..."; \
		cd webapp/frontend && npm run build && pm2 start "npx serve dist/ -s -l 8080" --name frontend --log-date-format="YYYY-MM-DD HH:mm Z"; \
	fi
	@-pm2 delete backend 2>/dev/null
	@cd webapp/backend && pm2 start "$(PYTHON) main.py" --name backend --log-date-format="YYYY-MM-DD HH:mm Z"
	@pm2 save
	@ADD_TEST=$$(grep "^ADD_TEST_DATA=" user_config/settings 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr '[:upper:]' '[:lower:]'); \
	if [ "$$ADD_TEST" = "true" ] || [ -z "$$ADD_TEST" ]; then \
		echo ""; \
		echo "$(GREEN)$(BOLD)Seed Test Data$(RESET)"; \
		echo "Creates test accounts and a server entry for development/testing:"; \
		echo "  - Admin user:  admin@foo.com (password: test)"; \
		echo "  - Normal user: user@foo.com (password: test)"; \
		echo "  - Server 'server1' with CPU/RAM/GPU hardware specs"; \
		echo ""; \
		echo "$(RED)$(BOLD)NOTE:$(RESET) If this is a first-time setup, it is $(GREEN)$(BOLD)HIGHLY recommended$(RESET) to seed test data."; \
		echo "Without it, there are no user accounts to log in with and the first-time"; \
		echo "setup expects the container server to be named 'server1'."; \
		echo ""; \
		echo "This prompt will not appear again on future restarts."; \
		echo "To seed test data later, run: $(GREEN)$(BOLD)make seed-data$(RESET)"; \
		echo ""; \
		echo -n "Seed test data? (y/N): "; \
		read SEED_CHOICE; \
		if [ "$$SEED_CHOICE" = "y" ] || [ "$$SEED_CHOICE" = "Y" ]; then \
			echo ""; \
			$(MAKE) seed-data; \
		else \
			echo ""; \
			echo "Skipped. Run $(GREEN)$(BOLD)make seed-data$(RESET) anytime to seed test data."; \
		fi; \
		if grep -q "^ADD_TEST_DATA=" user_config/settings 2>/dev/null; then \
			sed -i 's/^ADD_TEST_DATA=.*/ADD_TEST_DATA=false/' user_config/settings; \
		else \
			printf '\n\n# Set to true to prompt for seeding test data on next server start (make start-main-server)\n# This is automatically set to false after the prompt is shown.\n# You can also always run `make seed-data` anytime to seed manually.\nADD_TEST_DATA=false\n' >> user_config/settings; \
		fi; \
		echo ""; \
	fi
	@URL=$$(grep -o '"url": "[^"]*"' webapp/backend/settings.json | cut -d'"' -f4) && \
	echo "" && \
	echo "" && \
	echo "$(GREEN)$(BOLD)Servers started/restarted!$(RESET)" && \
	echo "Access at: $(GREEN)$(BOLD)$$URL$(RESET) (can take some time for the server to start)" && \
	echo "View logs: $(GREEN)$(BOLD)make logs$(RESET)" && \
	echo "" && \
	echo "$(GREEN)Note:$(RESET) Run this task again after changing settings or pulling updates to restart servers and apply changes." && \
	echo "" && \
	echo "Potential Next Step:" && \
	echo "* If you have not yet setup the container server, run $(GREEN)$(BOLD)sudo make setup-container-server$(RESET) to start setting it up.$(RESET)" && \
	echo ""

setup-container-server: check-root check-os-ubuntu interactive-docker-settings-creation apply-settings ## Run this with sudo. Setups the container server daemon. Call 'make start-container-server' after setup.
	@IS_MAIN_SERVER=$$(cat .server_type 2>/dev/null || echo "true"); \
	if [ "$$IS_MAIN_SERVER" = "false" ]; then \
		echo ""; \
		echo "$(GREEN)$(BOLD)FIREWALL CONFIGURATION$(RESET)"; \
		echo "$(GREEN)HIGHLY RECOMMENDED:$(RESET) Configure iptables firewall rules to secure your server."; \
		echo "This will:"; \
		echo "  - Enable iptables firewall with secure defaults"; \
		echo "  - $(RED)BLOCK ALL incoming connections except:$(RESET)"; \
		echo "    - SSH (22)"; \
		PORT_START=$$(grep "^DOCKER_RESERVATION_PORT_RANGE_START=" user_config/settings | cut -d'=' -f2 2>/dev/null || echo "2000"); \
		PORT_END=$$(grep "^DOCKER_RESERVATION_PORT_RANGE_END=" user_config/settings | cut -d'=' -f2 2>/dev/null || echo "3000"); \
		echo "    - Container ports ($$PORT_START-$$PORT_END)"; \
		ADDITIONAL_PORTS=$$(grep "^FIREWALL_ADDITIONAL_PORTS=" user_config/settings | cut -d'"' -f2 2>/dev/null || echo ""); \
		if [ -n "$$ADDITIONAL_PORTS" ]; then \
			echo "    - Additional ports ($$ADDITIONAL_PORTS)"; \
		fi; \
		echo "  - Secure Docker containers"; \
		echo ""; \
		echo "$(RED)WARNING:$(RESET) This will $(RED)RESET$(RESET) any existing iptables firewall rules!"; \
		echo ""; \
		echo "Configure firewall rules automatically?"; \
		echo "  $(GREEN)y$(RESET) - Yes, configure firewall rules (recommended)"; \
		echo "  $(GREEN)n$(RESET) - No, skip firewall configuration (not recommended)"; \
		echo "  NOTE: If you have already configured the firewall in the past, you can skip this step with option $(BOLD)n$(RESET)."; \
		echo -n "Choice (y/n): "; \
		read FIREWALL_CHOICE; \
		echo ""; \
		if [ "$$FIREWALL_CHOICE" = "y" ] || [ "$$FIREWALL_CHOICE" = "Y" ]; then \
			echo "$(GREEN)Configuring firewall rules...$(RESET)"; \
			$(MAKE) apply-firewall-rules; \
			echo "$(GREEN)Firewall configuration completed.$(RESET)"; \
		else \
			echo "$(RED)WARNING: Firewall not configured!$(RESET)"; \
			echo "Your server may be vulnerable to unauthorized access."; \
			echo "You can configure it later by running this command again."; \
			echo -n "Press Enter to continue with setup anyway..."; \
			read CONTINUE_ANYWAY; \
		fi; \
		echo ""; \
	else \
		echo ""; \
		echo "$(GREEN)Skipping firewall configuration - already configured during main server setup.$(RESET)"; \
		echo ""; \
	fi

	@chmod +x scripts/install_docker_dependencies.bash
	@./scripts/install_docker_dependencies.bash
	@REAL_USER=$${SUDO_USER:-$$(logname 2>/dev/null || echo $$(whoami))}; \
	usermod -aG docker $$REAL_USER; \
	echo "Added user $$REAL_USER to docker group"

	# Set containerfly group permissions on user home directory
	@echo "$(GREEN)Setting containerfly group permissions on user home directory...$(RESET)"
	@REAL_USER=$${SUDO_USER:-$$(logname 2>/dev/null || echo $$(whoami))}; \
	USER_HOME=$$(eval echo ~$$REAL_USER); \
	echo "Configuring ACL permissions for containerfly group on $$USER_HOME"; \
	echo "This allows containers to access your home directory when mounted."; \
	setfacl -m g:containerfly:rwx "$$USER_HOME" 2>/dev/null || echo "Warning: Could not set ACL on home directory"; \
	echo "Home directory permissions configured for containerfly group."

	# Automatically configure pm2 startup
	@echo "$(GREEN)Configuring pm2 startup...$(RESET)"
	@REAL_USER=$${SUDO_USER:-$$(logname 2>/dev/null || echo $$(whoami))}; \
	PM2_STARTUP_CMD=$$(sudo -u $$REAL_USER pm2 startup 2>/dev/null | grep "sudo env" || true); \
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
	@echo "2. Run $(BOLD)make start-container-server$(RESET)$(GREEN) to start the container server daemon.$(RESET)\n"
	@rm -f .server_type

setup-docker-utility: setup-container-server ## Alias for setup-container-server (backward compatibility)

start-container-server: check-not-root apply-settings ## Starts the container server daemon. The daemon starts, stops, and restarts reserved containers on this server via the backend REST API. Run this again after changing settings to restart.
	@echo ""
	@-pm2 delete backendDockerUtil 2>/dev/null
	@cd webapp/container_server && pm2 start "$(PYTHON) main.py" --name backendDockerUtil --log-date-format="YYYY-MM-DD HH:mm Z"
	@pm2 save
	@echo ""
	@echo "\n$(GREEN)$(BOLD)Container server daemon is now running.$(RESET)"
	@echo "Containers will now automatically start, stop, and restart on this server."
	@echo ""
	@echo "View logs: $(GREEN)$(BOLD)make logs$(RESET)"
	@echo ""
	@echo "$(GREEN)Note:$(RESET) Run this task again after changing settings to restart the container server and apply changes."
	@echo ""

start-docker-utility: start-container-server ## Alias for start-container-server (backward compatibility)

update-main-server: check-not-root verify-config-file-exists ## Pull latest code, update dependencies, and restart main server
	@echo ""
	@echo "$(GREEN)$(BOLD)Updating main server...$(RESET)"
	@echo ""
	@echo "Pulling latest code..."
	@git pull
	@echo ""
	@echo "Installing backend dependencies..."
	@$(PIP) install -r webapp/backend/requirements.txt --break-system-packages --ignore-installed --no-warn-script-location -qq
	@echo ""
	@echo "Installing frontend dependencies..."
	@cd webapp/frontend && npm install
	@echo ""
	@$(MAKE) start-main-server

update-container-server: check-not-root verify-config-file-exists ## Pull latest code, update dependencies, and restart container server
	@echo ""
	@echo "$(GREEN)$(BOLD)Updating container server...$(RESET)"
	@echo ""
	@echo "Pulling latest code..."
	@git pull
	@echo ""
	@echo "Installing container server dependencies..."
	@$(PIP) install -r webapp/container_server/requirements.txt --break-system-packages --ignore-installed --no-warn-script-location -qq
	@echo ""
	@$(MAKE) start-container-server

update-docker-utility: update-container-server ## Alias for update-container-server (backward compatibility)

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
	# Allow IP for general access
	sudo iptables -I INPUT -s $(IP) -j ACCEPT
	# Allow IP for Docker registry port 5000 access
	sudo iptables -I DOCKER-USER -s $(IP) -p tcp --dport 5000 -j ACCEPT
	sudo iptables -I DOCKER-USER -s $(IP) -p udp --dport 5000 -j ACCEPT

	# Save iptables rules to make them persistent
	@echo "Saving iptables rules for persistence..."
	@mkdir -p /etc/iptables
	@iptables-save > /etc/iptables/rules.v4
	@echo "iptables rules saved successfully"

logs: ## View log entries for started servers (pm2)
	pm2 logs --lines 10000

status: ## Views the status of the started servers (pm2)
	pm2 list

stop-servers: ## Kills (stops) the frontend, backend and docker utility servers (pm2 process manager)
	@-pm2 delete frontend 2>/dev/null || echo "frontend pm2 service was not running. Nothing to stop."
	@-pm2 delete backend 2>/dev/null || echo "backend pm2 service was not running. Nothing to stop."
	@-pm2 delete backendDockerUtil 2>/dev/null || echo "backendDockerUtil pm2 service was not running. Nothing to stop."
	@echo "\n$(GREEN)Servers stopped!$(RESET)"


seed-data: check-not-root verify-config-file-exists ## Seed test data (admin user, normal user, test server with hardware specs)
	@cd $(BACKEND_PATH) && $(PYTHON) ../../scripts/seed_test_data.py

interactive-docker-settings-creation: # Creates Docker utility settings interactively
	@echo ""
	@echo "$(GREEN)$(BOLD)Server Type Configuration:$(RESET)"
	@echo "Are you setting up a Docker utility for:"
	@echo "  $(GREEN)1$(RESET) - Main server (same machine as web interface)"
	@echo "  $(GREEN)2$(RESET) - Separate container server (different machine)"
	@echo -n "Enter your choice (1 or 2): "
	@read SERVER_TYPE_CHOICE; \
	\
	case "$$SERVER_TYPE_CHOICE" in \
		1) \
			echo "Setting up Docker utility for main server..."; \
			IS_MAIN_SERVER=true; \
			DEFAULT_SERVER_NAME="server1"; \
			;; \
		2) \
			echo "Setting up Docker utility for separate container server..."; \
			IS_MAIN_SERVER=false; \
			DEFAULT_SERVER_NAME="server2"; \
			;; \
		*) \
			echo "$(RED)Invalid choice. Setup cancelled.$(RESET)"; \
			exit 1; \
			;; \
	esac; \
	echo "$$IS_MAIN_SERVER" > .server_type; \
	\
	if [ ! -e $(CONFIG_SETTINGS) ]; then \
		RECONFIGURE_SETTINGS=true; \
		FIRST_TIME_SETUP=true; \
	else \
		EXISTING_SERVER_IP=$$(grep "^SERVER_IP_ADDRESS=" user_config/settings | cut -d'"' -f2); \
		EXISTING_SERVER_NAME=$$(grep "^DOCKER_SERVER_NAME=" user_config/settings | cut -d'"' -f2); \
		EXISTING_PORT_START=$$(grep "^DOCKER_RESERVATION_PORT_RANGE_START=" user_config/settings | cut -d'=' -f2); \
		EXISTING_PORT_END=$$(grep "^DOCKER_RESERVATION_PORT_RANGE_END=" user_config/settings | cut -d'=' -f2); \
		EXISTING_REGISTRY_ADDRESS=$$(grep "^DOCKER_REGISTRY_ADDRESS=" user_config/settings | cut -d'=' -f2 | tr -d '"'); \
		if [ -z "$$EXISTING_REGISTRY_ADDRESS" ] || [ "$$EXISTING_REGISTRY_ADDRESS" = '""' ]; then \
			EFFECTIVE_REGISTRY_ADDRESS="$$EXISTING_SERVER_IP (default)"; \
		else \
			EFFECTIVE_REGISTRY_ADDRESS=$$EXISTING_REGISTRY_ADDRESS; \
		fi; \
		\
		echo ""; \
		echo "$(GREEN)Docker settings file exists with current configuration:$(RESET)"; \
		echo "  - Current Server IP: $(GREEN)$$EXISTING_SERVER_IP$(RESET)"; \
		echo "  - Docker Server Name: $(GREEN)$$EXISTING_SERVER_NAME$(RESET)"; \
		echo "  - Port Range: $(GREEN)$$EXISTING_PORT_START - $$EXISTING_PORT_END$(RESET)"; \
		echo "  - Registry Address: $(GREEN)$$EFFECTIVE_REGISTRY_ADDRESS$(RESET)"; \
		echo "  - Registry Port: $(GREEN)5000$(RESET)"; \
		EXISTING_DAEMON_KEY=$$(grep "^DAEMON_API_KEY=" user_config/settings | cut -d'"' -f2); \
		if [ -n "$$EXISTING_DAEMON_KEY" ]; then \
			MASKED_KEY="$$(echo "$$EXISTING_DAEMON_KEY" | cut -c1-8)..."; \
			echo "  - Daemon API Key: $(GREEN)$$MASKED_KEY$(RESET)"; \
		else \
			echo "  - Daemon API Key: $(RED)not set$(RESET)"; \
		fi; \
		if [ "$$IS_MAIN_SERVER" = "false" ]; then \
			echo ""; \
			echo "  $(BOLD)NOTE:$(RESET) DAEMON_API_KEY in user_config/settings must match the same key in your"; \
			echo "  main server user_config/settings file. The container server uses it to connect"; \
			echo "  to the main server Web REST API."; \
		fi; \
		echo ""; \
		echo "What would you like to do?"; \
		echo "  $(GREEN)1$(RESET) - Use these settings and proceed with setup"; \
		echo "  $(GREEN)2$(RESET) - Reconfigure all Docker utility settings"; \
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
		if [ "$$IS_MAIN_SERVER" = "true" ]; then \
			CURRENT_SERVER_IP=$$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' || echo "127.0.0.1"); \
			REGISTRY_ADDRESS=$$CURRENT_SERVER_IP; \
			SERVER_IP_ADDRESS=$$CURRENT_SERVER_IP; \
		else \
			echo ""; \
			echo "$(GREEN)$(BOLD)Main Server IP Configuration:$(RESET)"; \
			echo -n "Enter the IP address of your main server: "; \
			read MAIN_SERVER_IP; \
			REGISTRY_ADDRESS=$$MAIN_SERVER_IP; \
			CURRENT_SERVER_IP=$$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' || echo "127.0.0.1"); \
			SERVER_IP_ADDRESS=$$CURRENT_SERVER_IP; \
			echo ""; \
			echo "$(GREEN)$(BOLD)Daemon API Key:$(RESET)"; \
			echo "The container server uses this key to connect to the main server REST API."; \
			echo "It must match the $(GREEN)DAEMON_API_KEY$(RESET) value in $(GREEN)user_config/settings$(RESET) on your main server."; \
			echo -n "Enter the daemon API key: "; \
			read DAEMON_KEY_INPUT; \
		fi; \
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
		if [ -n "$$DAEMON_KEY_INPUT" ]; then \
			DAEMON_KEY_ESCAPED=$$(printf '%s\n' "$$DAEMON_KEY_INPUT" | sed 's/[\/&]/\\&/g'); \
			sed -i "s/^DAEMON_API_KEY=.*/DAEMON_API_KEY=\"$$DAEMON_KEY_ESCAPED\"/" user_config/settings; \
		fi; \
	fi; \
	\
	echo ""; \
	echo "$(GREEN)$(BOLD)Configuration completed successfully!$(RESET)"; \
	echo ""; \
	echo "$(GREEN)$(BOLD)!! IMPORTANT !!$(RESET) Please take a moment to manually review the full $(GREEN)user_config/settings$(RESET) file"; \
	echo "as it contains additional optional settings that you may want to configure for your setup."; \
	echo ""; \
	echo "What would you like to do?"; \
	echo "  $(GREEN)1$(RESET) - Settings are correct - Proceed with Docker utility installation"; \
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
	esac

backup-database: verify-config-file-exists ## Create a database backup using mysqldump. Optionally specify path: make backup-database DEST=~/backups/
	@DB_HOST=$$(grep "^MARIADB_SERVER_ADDRESS=" user_config/settings | cut -d'"' -f2); \
	DB_NAME=$$(grep "^MARIADB_DB_NAME=" user_config/settings | cut -d'"' -f2); \
	DB_USER=$$(grep "^MARIADB_DB_USER=" user_config/settings | cut -d'"' -f2); \
	DB_PASS=$$(grep "^MARIADB_DB_USER_PASSWORD=" user_config/settings | cut -d'"' -f2); \
	BACKUP_DEST=$${DEST:-~}; \
	BACKUP_DEST=$$(eval echo "$$BACKUP_DEST"); \
	if [ -d "$$BACKUP_DEST" ]; then \
		TIMESTAMP=$$(date +%Y_%m_%d_%H_%M_%S); \
		BACKUP_PATH="$$BACKUP_DEST/backup_containers_fly_$$TIMESTAMP.sql"; \
	else \
		BACKUP_PATH="$$BACKUP_DEST"; \
	fi; \
	echo ""; \
	echo "$(GREEN)$(BOLD)Backing up database '$$DB_NAME' to $$BACKUP_PATH...$(RESET)"; \
	echo ""; \
	mysqldump -h "$$DB_HOST" -u "$$DB_USER" -p"$$DB_PASS" "$$DB_NAME" > "$$BACKUP_PATH"; \
	if [ $$? -eq 0 ]; then \
		echo "$(GREEN)Database backup saved to $$BACKUP_PATH$(RESET)"; \
	else \
		echo "$(RED)Database backup failed$(RESET)"; \
		rm -f "$$BACKUP_PATH"; \
		exit 1; \
	fi

init-database: ## Initialize database (for both new and existing environments)
	@echo ""
	@echo "Initializing database..."
	@cd $(BACKEND_PATH) && $(PYTHON) -m helpers.init_database
	@echo "Stopping all pm2 processes to prevent database locks..."
	@pm2 stop all || true
	@echo ""
	@echo "Running any pending migrations..."
	@echo "$(BOLD)NOTE:$(RESET) If migration gets stuck here and does not proceed further, it may be due to container server(s) holding database connections."
	@echo "    If that happens, then on each container server, run: $(BOLD)pm2 stop all$(RESET). Wait for migration to complete, then run: $(BOLD)pm2 restart all$(RESET) on each container server."
	@echo ""
	@cd $(BACKEND_PATH) && alembic upgrade head
	@echo "$(GREEN)Restarting all pm2 processes...$(RESET)"
	@pm2 restart all || true

migrate-database: ## Run database migrations
	@echo "Running database migrations..."
	@echo "$(BOLD)NOTE:$(RESET) If migration gets stuck, it may be due to container server(s) holding database connections."
	@echo "$(RED)      On each container server, run: pm2 stop all$(RESET)"
	@echo "$(RED)      Wait for migration to complete, then run: pm2 restart all$(RESET)"
	@echo ""
	@cd $(BACKEND_PATH) && alembic upgrade head

create-migration: ## Create a new database migration (use MESSAGE="your message")
	@echo "Creating new migration..."
	@cd $(BACKEND_PATH) && alembic revision --autogenerate -m "$(MESSAGE)"

# ===========================================================================
# Testing
# ===========================================================================

test-backend-unit: ## Run backend unit tests
	@cd $(BACKEND_PATH) && $(PYTHON) -m pytest ../../tests/backend/unit -v

test-backend-integration: ## Run backend integration tests
	@cd $(BACKEND_PATH) && $(PYTHON) -m pytest ../../tests/backend/integration -v

test-backend: ## Run all backend tests
	@cd $(BACKEND_PATH) && $(PYTHON) -m pytest ../../tests/backend -v

test-backend-coverage: ## Run backend tests with coverage report
	@cd $(BACKEND_PATH) && $(PYTHON) -m pytest ../../tests/backend -v --cov=. --cov-report=html

test-container-server-unit: ## Run container server unit tests
	@cd $(CONTAINER_SERVER_PATH) && $(PYTHON) -m pytest ../../tests/container_server/unit -v

test-container-server: ## Run all container server tests
	@cd $(CONTAINER_SERVER_PATH) && $(PYTHON) -m pytest ../../tests/container_server -v

test-container-server-coverage: ## Run container server tests with coverage report
	@cd $(CONTAINER_SERVER_PATH) && $(PYTHON) -m pytest ../../tests/container_server -v --cov=. --cov-report=html

test-frontend: ## Run frontend unit and component tests
	@cd webapp/frontend && npx vitest run

test-frontend-watch: ## Run frontend tests in watch mode
	@cd webapp/frontend && npx vitest

test-e2e-setup: ## Create temporary test users for E2E/API tests
	@cd $(BACKEND_PATH) && $(PYTHON) ../../tests/scripts/setup_test_users.py

test-e2e-teardown: ## Remove temporary test users
	@cd $(BACKEND_PATH) && $(PYTHON) ../../tests/scripts/teardown_test_users.py

test-e2e: ## Run Playwright E2E tests (requires running app stack)
	@cd $(BACKEND_PATH) && $(PYTHON) ../../tests/scripts/setup_test_users.py
	@cd tests/e2e && npm test; EXIT=$$?; \
	  cd ../.. && cd $(BACKEND_PATH) && $(PYTHON) ../../tests/scripts/teardown_test_users.py; \
	  exit $$EXIT

test-e2e-ui: ## Run Playwright E2E tests with UI (requires running app stack)
	@cd $(BACKEND_PATH) && $(PYTHON) ../../tests/scripts/setup_test_users.py
	@cd tests/e2e && npx --no-install playwright test --ui; EXIT=$$?; \
	  cd ../.. && cd $(BACKEND_PATH) && $(PYTHON) ../../tests/scripts/teardown_test_users.py; \
	  exit $$EXIT

test-api: ## Run Bruno CLI API tests (requires running app)
	@cd $(BACKEND_PATH) && $(PYTHON) ../../tests/scripts/setup_test_users.py
	@cd $(BACKEND_PATH) && $(PYTHON) ../../tests/scripts/generate_bruno_env.py
	@cd tests/api && npx --no-install bru run --env test -r; EXIT=$$?; \
	  cd ../.. && cd $(BACKEND_PATH) && $(PYTHON) ../../tests/scripts/teardown_test_users.py; \
	  exit $$EXIT

test-all: ## Run backend + container server + frontend tests (not E2E — those need a running app)
	@$(MAKE) test-backend
	@$(MAKE) test-container-server
	@$(MAKE) test-frontend


# ===========================================================================
# Documentation
# ===========================================================================

generate-db-diagram: ## Generate database ER diagram from SQLAlchemy models (Mermaid)
	@echo "Generating database diagram..."
	@$(PYTHON) scripts/generate_db_diagram.py
	@echo "$(GREEN)Database diagram generated: additional_documentation/database_diagram.md$(RESET)"

generate-db-diagram-png: generate-db-diagram ## Generate database ER diagram as PNG (requires Node.js)
	@echo "Rendering diagram to PNG..."
	@npx -y @mermaid-js/mermaid-cli mmdc -i additional_documentation/database_diagram.md -o additional_documentation/database_diagram.png -t neutral -b white -w 2400
	@echo "$(GREEN)Database diagram PNG generated: additional_documentation/database_diagram.png$(RESET)"