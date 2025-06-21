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

verify-config-file-exists: # Verify that the main configuration file exists.
	@if [ ! -e $(CONFIG_SETTINGS) ]; then \
		echo "Error: $(CONFIG_SETTINGS) does not exist. Please copy user_config/settings_example to user_config/settings and configure it first."; \
		exit 1; \
	fi

check-os-ubuntu: # Checks if the operating system is Ubuntu. Stops executing if not.
	@OS_NAME=$$(lsb_release -si 2>/dev/null || echo "Unknown") && \
	if [ "$$OS_NAME" != "Ubuntu" ]; then \
		echo "\n$(RED)Error: This setup script is only compatible with Ubuntu Linux. Please refer to the readme documentation for manual steps. Exiting.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Operating system is Ubuntu Linux. Proceeding with setup.$(RESET)"

apply-settings: # Applies the settings from user_config/settings to template files and generates configuration files.
	@chmod +x scripts/apply_settings.py
	@$(PYTHON) scripts/apply_settings.py

# Production targets

setup-main-server: check-os-ubuntu verify-config-file-exists apply-settings apply-firewall-rules ## Installs and configures all dependencies for main server. Only works on Ubuntu Linux. If using any other operating system, then refer to the readme documentation for manual steps. Call 'make start-main-server' after setup.
	@chmod +x scripts/install_webserver_dependencies.bash
	@./scripts/install_webserver_dependencies.bash
	sudo -u $${SUDO_USER:-$(shell whoami)} $(PIP) install -r webapp/backend/requirements.txt --break-system-packages --ignore-installed
	# Fix ownership of frontend directory first to avoid permission issues
	@chown -R $${SUDO_USER:-$(shell whoami)}:$${SUDO_USER:-$(shell whoami)} webapp/frontend/ 2>/dev/null || true
	# Install frontend dependencies as the original user
	cd webapp/frontend && sudo -u $${SUDO_USER:-$(shell whoami)} npm install

	@echo "\n$(GREEN)The main server has been setup.\n"
	@echo "NEXT STEPS:"
	@echo "1. Run command $(BOLD)pm2 startup$(RESET)$(GREEN) and copy/paste the command to your terminal."
	@echo "2. Restart the machine for all the changes to take effect.$(RESET)\n"

start-main-server: verify-config-file-exists apply-settings ## Starts all the main server services or restarts them if started. Nginx is used to create a reverse proxy. pm2 process manager is used to run the frontend and backend.
	@systemctl reload nginx
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