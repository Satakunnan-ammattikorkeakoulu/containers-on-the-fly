PYTHON=python3
PIP=pip

# Define variables
BACKEND_PATH = webapp/backend
BACKEND_SRC = main.py
FOLDER_SRC=src
APP_ENTRYPOINT=$(FOLDER_SRC)/main.py
CONFIG_SETTINGS = "user_config/settings"
CONFIG_BACKEND_SETTINGS = "user_config/backend_settings.json"
CONFIG_FRONTEND_SETTINGS = "user_config/frontend_settings.js"
CONFIG_NGINX_SETTINGS = "user_config/nginx_settings.conf"

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

verify-all-config-files-exist: # Verify that all configuration files exists in the user_config folder.
	@if [ ! -e $(CONFIG_SETTINGS) ]; then \
		echo "Error: $(CONFIG_SETTINGS) does not exist. Please copy the example settings file from the user_config/examples folder to user_config location and write your own configurations first."; \
		exit 1; \
	fi
	@if [ ! -e $(CONFIG_BACKEND_SETTINGS) ]; then \
		echo "Error: $(CONFIG_BACKEND_SETTINGS) does not exist. Please copy the example settings file from the user_config/examples folder to user_config location and write your own configurations first."; \
		exit 1; \
	fi
	@if [ ! -e $(CONFIG_FRONTEND_SETTINGS) ]; then \
		echo "Error: $(CONFIG_FRONTEND_SETTINGS) does not exist.  Please copy the example settings file from the user_config/examples folder to user_config location and write your own configurations first."; \
		exit 1; \
	fi
	@if [ ! -e $(CONFIG_NGINX_SETTINGS) ]; then \
		echo "Error: $(CONFIG_NGINX_SETTINGS) does not exist.  Please copy the example settings file from the user_config/examples folder to user_config location and write your own configurations first."; \
		exit 1; \
	fi

check-os-ubuntu: # Checks if the operating system is Ubuntu. Stops executing if not.
	@OS_NAME=$$(lsb_release -si 2>/dev/null || echo "Unknown") && \
	if [ "$$OS_NAME" != "Ubuntu" ]; then \
		echo "\n$(RED)Error: This setup script is only compatible with Ubuntu Linux. Please refer to the readme documentation for manual steps. Exiting.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Operating system is Ubuntu Linux. Proceeding with setup.$(RESET)"

merge-settings: # Merges the settings file into frontend and backend settings.
	@chmod +x scripts/merge_settings.bash
	@./scripts/merge_settings.bash

# Production targets

setup-main-server: check-os-ubuntu verify-all-config-files-exist apply-firewall-rules ## Installs and configures all dependencies for main server. Only works on Ubuntu Linux. If using any other operating system, then refer to the readme documentation for manual steps. Call 'make start-main-server' after setup.
	@chmod +x scripts/install_webserver_dependencies.bash
	@./scripts/install_webserver_dependencies.bash
	$(PIP) install -r webapp/backend/requirements.txt
	# Need to run the next command without sudo, as otherwise the node_modules folder created would be owned by root
	cd webapp/frontend && sudo -u $(shell who am i | awk '{print $$1}') npm install

	@echo "\n$(GREEN)The main server has been setup.\n"
	@echo "NEXT STEPS:"
	@echo "1. Run command $(BOLD)pm2 startup$(RESET)$(GREEN) and copy/paste the command to your terminal."
	@echo "2. Restart the machine for all the changes to take effect.$(RESET)\n"

start-main-server: verify-all-config-files-exist merge-settings ## Starts all the main server services or restarts them if started. Nginx is used to create a reverse proxy. pm2 process manager is used to run the frontend and backend.
	@cp user_config/backend_settings.json webapp/backend/settings.json
	@cp user_config/frontend_settings.js webapp/frontend/src/AppSettings.js
	@systemctl reload nginx
	@cd webapp/frontend && pm2 restart frontend 2>/dev/null || pm2 start "npm run production" --name frontend --log-date-format="YYYY-MM-DD HH:mm Z"
	@cd webapp/backend && pm2 restart backend 2>/dev/null || pm2 start "$(PYTHON) main.py" --name backend --log-date-format="YYYY-MM-DD HH:mm Z"
	@pm2 save
	@URL=$$(grep '"url"' user_config/backend_settings.json | sed 's/.*"url": "\(.*\)".*/\1/') && \
	echo "" && \
	echo "$(GREEN)Web servers (nginx proxy, frontend, backend) have been started / restarted!$(RESET)" && \
	echo "Access the launched web interface at: $(GREEN)$$URL$(RESET) (it can take several seconds for the server to launch)" && \
	echo "You can view any logs (errors) using the $(GREEN)make logs$(RESET) command."

setup-docker-utility: ## Setups the Docker utility. The Docker utility will start, stop, and restart the containers on this machine. Call 'make start-docker-utility' after setup.
	# Check that the backend settings configuration file exists
	@if [ ! -e $(CONFIG_BACKEND_SETTINGS) ]; then \
		echo "Error: $(CONFIG_BACKEND_SETTINGS) does not exist. This utility uses the $(CONFIG_BACKEND_SETTINGS) file to connect to the database, please configure this file first."; \
		exit 1; \
	fi
	@chmod +x scripts/install_docker_dependencies.bash
	@./scripts/install_docker_dependencies.bash
	@$(PIP) install -r webapp/backend/requirements.txt
	@usermod -aG docker $(shell who am i | awk '{print $$1}')
	@echo "\n$(GREEN)The Docker utility has been setup.\n"
	@echo "NEXT STEPS:"
	@echo "1. Run command $(BOLD)pm2 startup$(RESET)$(GREEN) and copy/paste the command to your terminal."
	@echo "2. Restart the machine for all the changes to take effect.$(RESET)\n"

start-docker-utility: merge-settings ## Starts the Docker utility. The utility starts, stops, restarts reserved containers on this server. pm2 process manager is used to run the script in the background.
	@echo "Verifying that connection to the database can be made using the $(CONFIG_BACKEND_SETTINGS) setting engineUri..."
	@CONNECTION_URI=$$(grep '"engineUri"' $(CONFIG_BACKEND_SETTINGS) | sed 's/.*"engineUri": "\(.*\)".*/\1/') && \
	CONNECTION_OK=$$($(PYTHON) scripts/verify_db_connection.py "$$CONNECTION_URI") && \
	if [ "$$CONNECTION_OK" = "CONNECTION_OK" ]; then \
		echo "Connection to the database was successful. Proceeding."; \
	else \
		echo "\n$(RED)Connection to the database could not be established. Please check that you have the $(CONFIG_BACKEND_SETTINGS) setting engineUri properly set and that connection to the database can be made (firewalls etc...).$(RESET)"; \
		exit 1; \
	fi

	@cp user_config/backend_settings.json webapp/backend/settings.json
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

start-dev-frontend: merge-settings
	@cp user_config/backend_settings.json webapp/backend/settings.json
	@cp user_config/frontend_settings.js webapp/frontend/src/AppSettings.js
	cd webapp/frontend && npm run serve

start-dev-backend: merge-settings
	@cp user_config/backend_settings.json webapp/backend/settings.json
	@cp user_config/frontend_settings.js webapp/frontend/src/AppSettings.js
	cd webapp/backend && $(PYTHON) main.py

start-dev-docker-utility: merge-settings
	@cp user_config/backend_settings.json webapp/backend/settings.json
	@cp user_config/frontend_settings.js webapp/frontend/src/AppSettings.js
	cd webapp/backend && $(PYTHON) dockerUtil.py