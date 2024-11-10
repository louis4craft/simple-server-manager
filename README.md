Minecraft Server Manager

Description:
The Minecraft Server Manager allows you to easily manage your Minecraft server directly from the console. With this tool, you can start and stop your server, manage players, create and restore backups, and save player playtimes. Additionally, you can retrieve player positions, view the list of online players, and manage the server's whitelist.
Key Features:

    Start and stop your Minecraft server
    Manage players (kick, ban, unban)
    Create and restore backups of the Minecraft server
    Save player playtimes
    Retrieve player positions
    Display the current list of players and the server whitelist

Requirements:

Python 3
Java (required to run the Minecraft server)

Configuration:

In the config.py file, you can set the language for the server manager. Additionally, you'll need to specify the path to your Minecraft server's JAR file.
Initial Setup:

When you run the server for the first time, it will automatically shut down. This is because you need to accept the Minecraft EULA (End User License Agreement). To do this:

1. Open the eula.txt file located in the server directory.
2. Change the line:

eula=false

to:

eula=true

Save the file and restart the server.

Once the EULA is accepted, the server should start successfully.
