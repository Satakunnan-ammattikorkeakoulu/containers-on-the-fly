# Containers on the Fly
> Instant Up. Timely Down. Simple web-based Docker container reservation platform.

<img width="500" alt="image 7" src="https://github.com/Satakunnan-ammattikorkeakoulu/containers-on-the-fly/assets/3810422/61a9d8d4-c788-4528-a245-3930543a7a34">

## Description

With this Web app, users permitted to access the app can easily reserve Docker containers with hardware resources needed for their projects. The user can select the start and end time for the container reservation. Multiple servers can be integrated for reservations.

Users can login with username & password combination, or through LDAP. Includes also admin-level management tools in the web app.

Originally created in Satakunta University of Applied Sciences to give AI students a solution to handle their AI calculating in a dedicated server.

## Screenshots

![image](https://user-images.githubusercontent.com/3810422/197523647-d603e763-fbf8-42cc-b211-1ca1343e2550.png)

![image](https://user-images.githubusercontent.com/3810422/197523756-0b1d79fb-64ed-4a86-a0a6-aed6a0757dab.png)

![image](https://user-images.githubusercontent.com/3810422/197523917-237ddd05-d35c-4d76-917d-963e60144598.png)

![image](https://user-images.githubusercontent.com/3810422/197524065-1a6b3452-e449-458c-a703-edd699a43f3b.png)

## Getting Started

![image](/additional_documentation/architecture.png)

The installation consists of two parts:
- the ``Main Server``, which contains the web servers (web interface), database, and local docker registry. All Docker images will be added to the local docker registry and other servers can then utilize these images from one server.
- ``Container Server(s)`` from which the virtual Docker reservations can be made. The container server can reside at the same location as the Main Server, or in multiple other servers. Users can make container reservations from these Container Servers.

### Automatic Installation: Main Server

> Heads up! The automatic installation script for the **main server** only works with Ubuntu Linux 22.04. It is HIGHLY RECOMMENDED to use a fresh Ubuntu installation, due to various software being installed and configured. For any other operating system, the installation procedure is required to be [conducted manually](#manual-installation-:-main-server).

The installation procedure of the Main Server (web servers, database, local Docker registry) is as follows:

#### Copy Configurations

Copy the settings files from `user_config/examples` to `user_config` folder. If you do not require an SSL certificate (your web interface is accessed using the HTTP protocol), then copy the `nginx_settings.conf` file. If you plan to use an SSL certificate (your web server will be accessed using the HTTPS protocol) then copy the file `nginx_settings_ssl.conf`.

#### Create Configurations

After copying the files, make configurations to the files. You can mainly start with the `user_config/settings` file first, and then look at the other files to determine if there is something more specific to configure.

#### Setup the Servers

After the configurations are ready, start setting up web servers with the command:

```bash
sudo make setup-webservers
```

#### Start the Servers

After the web server setup is complete, run the servers with:

```bash
make run-webservers
```

That's it! Now you should be able to access the web interface using a browser. There will be more information printed on your console after running the `make run-webservers` command.

### Automatic Installation: Container Server

> The automatic installation fo the Container Server 

The installation procedure of the Container Server is as follows:

#### Copy Configurations

Copy the settings files `user_config/examples/settings` and `user_config/examples/backend_settings.json` to the `user_config` folder.

#### Create Configurations

After copying the files, make configurations to the files.

#### Setup the Docker Utility

After the configurations are ready, set up the docker utility with:

```bash
make setup-docker-utility
```

#### Start Docker Utility

After the setup is complete, run the Docker utility with:

```bash
make run-docker-utility
```

That's it!

### Manual Installation: Main Server

The installation procedure of the Main Server (web servers, database, local Docker registry) is as follows:

##### Install Dependencies

Install:
- Python
- Pip
- Nginx
- MariaDB
- pm2 Process Manager
- NPM & NodeJS (version 20)

##### Configure the Dependencies

Set MariaDB to launch at startup.

In MariaDB, create a database and a user that has access to it.

Disable the default nginx site:
```
sudo rm /etc/nginx/sites-enabled/default
```

Add custom nginx configurations to the nginx file:
```
sudo sed -i "/http {/a \\    include /path/to/your/user_config/nginx_settings.conf;" /path/to/your/user_config/nginx_settings.conf
```

##### Copy Configurations

Copy the settings files from `user_config/examples` to `user_config` folder. If you do not require an SSL certificate (your web interface is accessed using the HTTP protocol), then copy the `nginx_settings.conf` file. If you plan to use an SSL certificate (your web server will be accessed using the HTTPS protocol) then copy the file `nginx_settings_ssl.conf`.

##### Create Configurations

After copying the files, make configurations to the files. You can mainly start with the `user_config/settings` file first, and then look at the other files to determine if there is something more specific to configure.

##### Start the Servers

After the web server setup is complete, run the servers with:

```bash
make run-webservers
```

That's it! Now you should be able to access the web interface using a browser. There will be more information printed on your console after running the `make run-webservers` command.

## Technical Details

The app is split into two projects: frontend and backend. The frontend can be located from `webapp/frontend` and backend from `webapp/backend`. Both the frontend and backend will run on different ports. The backend also includes a separate script for starting and stopping the reserved containers, called `dockerUtil.py`.

### Frontend

The frontend has been developed using Vue 2.

### Backend

The backend has been developed using Python 3, SQLAlchemy and FastAPI.

The backend also includes a tool called `dockerUtils.py` that handles starting and stopping the reserved containers.