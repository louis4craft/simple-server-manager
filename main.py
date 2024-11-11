# Coded By Louis4Craft (Verison 1.0)

import os
import subprocess
import shutil
import socket
import sqlite3
import zipfile
import time
import json
import threading
from datetime import datetime
import re
import config
from language import translations

if not os.path.exists("./manager"):
    os.mkdir("manager")


class MinecraftServer:
    def __init__(self):
        self.server_path      = config.SERVER_PATH
        self.server_dir       = os.path.dirname(self.server_path)
        self.backup_dir       = os.path.join(self.server_dir, "backups") 
        self.server_process   = None
        self.db_path          = os.path.join(self.server_dir, "manager", "data.db")
        self.conn             = self.setup_db()
        self.playtime_thread  = threading.Thread(target=self.update_playtime_thread, daemon=True)

    #--konsolen ausgaben löschen--#
    def clear_console(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    #--Datenbank initialisieren--#
    def setup_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS player_playtime (player TEXT, playtime INTEGER)")
            c.execute("CREATE TABLE IF NOT EXISTS player_stats (player TEXT, kills INTEGER, deaths INTEGER)")
            conn.commit()
            return conn
        except Exception as e:
            print(f"{translations[config.LANGUAGE]["error"]}: {e}")

    #--Haupt menu ausgeben--#
    def print_menu(self):
        print("\n=== Minecraft Server Manager ===")

        print(f"1. {translations[config.LANGUAGE]["start_server"]}")
        print(f"2. {translations[config.LANGUAGE]["get_players"]}")
        print(f"3. {translations[config.LANGUAGE]["ban_player"]}")
        print(f"4. {translations[config.LANGUAGE]["unban_player"]}")
        print(f"5. {translations[config.LANGUAGE]["kick_player"]}")
        print(f"6. {translations[config.LANGUAGE]["get_whitelist"]}")
        print(f"7. {translations[config.LANGUAGE]["player_info"]}")
        print(f"8. {translations[config.LANGUAGE]["stop_server"]}")
        print(f"9. {translations[config.LANGUAGE]["create_backup"]}")
        print(f"10. {translations[config.LANGUAGE]["load_backup"]}")
        print(f"11. {translations[config.LANGUAGE]["server_info"]}")


    #--Befehl an den minecraft server senden--#
    def send_command(self, command):
        if self.server_process and self.server_process.stdin:
            try:
                self.server_process.stdin.write(f"{command}\n")
                self.server_process.stdin.flush()
            except BrokenPipeError:
                print("Error: Server process is not available.")

    
    #--minecraft server starten--#
    def start_server(self, max_ram):
        if self.server_process:
            print(translations[config.LANGUAGE]["already_running"])
            return

        self.clear_console()
        print(translations[config.LANGUAGE]["server_starting"])
        input(translations[config.LANGUAGE]["continur_menu"])
        self.clear_console()

        java_cmd = [
            'java',
            f'-Xmx{max_ram}M',
            f'-Xms{max_ram // 1024}M',
            '-jar',
            self.server_path
        ]

        self.server_process = subprocess.Popen(
            java_cmd,
            cwd=self.server_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        if not self.playtime_thread or not self.playtime_thread.is_alive():
            self.playtime_thread = threading.Thread(target=self.update_playtime_thread, daemon=True)
            self.playtime_thread.start()

    def stop_server(self):
        if self.server_process:
            print(translations[config.LANGUAGE]["server_stoping"])
            try:
                self.send_command("stop")
                self.server_process.wait()
                self.server_process = None
                print(translations[config.LANGUAGE]["succes_stop"])
            except Exception as e:
                print(f"{translations[config.LANGUAGE]["error_stop"]}: {e}")
        else:
            print(translations[config.LANGUAGE]["not_running"])

    #--Backup Erstellen--#
    def create_backup(self):
        try:
            print(translations[config.LANGUAGE]["backup_creating"])
            backup_dir = os.path.join(self.server_dir, self.backup_dir)
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y:%m:%d_%H:%M")
            backup_name = f"backup_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)

            world_folders = ["world", "world_nether", "world_the_end"]
            temp_backup_dir = os.path.join(backup_dir, "temp_backup")
            os.makedirs(temp_backup_dir, exist_ok=True)

            backup_meta = {
                'timestamp' : timestamp,
                'worlds'    : world_folders,
                'version'   : 'unknown'
            }

            for folder in world_folders:
                world_path = os.path.join(self.server_dir, folder)
                if os.path.exists(world_path):  # Überprüft, ob der Ordner existiert
                    shutil.copytree(world_path, os.path.join(temp_backup_dir, folder))

            with open(os.path.join(temp_backup_dir, 'backup_meta.json'), "w") as f:
                json.dump(backup_meta, f, indent=4)

            with zipfile.ZipFile(f"{backup_path}.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_backup_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_backup_dir)
                        zipf.write(file_path, arcname)

            shutil.rmtree(temp_backup_dir)

            print(translations[config.LANGUAGE]["backup_succes"])
            return f"{backup_path}.zip"
    
        except Exception as e:
            return f"{translations[config.LANGUAGE]["error_backup"]}: {e}"
        
    #--Backup laden--#
    def load_backup(self, backup_file):
        try:
            if not os.path.exists(backup_file):
                print(translations[config.LANGUAGE]["backup_file_err"])
                return False
            
            restore_temp = os.path.join(self.server_dir, "restore_temp")
            os.makedirs(restore_temp, exist_ok=True)

            with zipfile.ZipFile(backup_file, "r") as zipf:
                zipf.extractall(restore_temp)

            meta_path = os.path.join(restore_temp, "backup_meta.json")
            backup_timestamp = ""
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    backup_meta = json.load(f)
                    backup_timestamp = backup_meta['timestamp']
                    
            if self.server_process:
                self.send_command(f"say {translations[config.LANGUAGE]["stopping_msg"]}")
                time.sleep(3)
                self.stop_server()
                time.sleep(10)
                print(f"{translations[config.LANGUAGE]["backup_load_1"]} {backup_timestamp} {translations[config.LANGUAGE]["backup_load_2"]}")

            for folder in ["world", "world_nether", "world_the_end"]:
                source = os.path.join(restore_temp, folder)
                destination = os.path.join(self.server_dir, folder)

                if os.path.exists(source):
                    if os.path.exists(destination):
                        shutil.rmtree(destination)

                    shutil.copytree(source, destination)

            shutil.rmtree(restore_temp)

            print(translations[config.LANGUAGE]["load_succes"])
            return True
    
        except Exception as e:
            print(f"{translations[config.LANGUAGE]["error_loading"]} {e}")
            return False
        

    #--Backups auflisten--#
    def list_backups(self):
        backup_dir = os.path.join(self.server_dir, "backups")
        if not os.path.exists(backup_dir):
            print(translations[config.LANGUAGE]["backup_not_found"])
            return []
        
        backups = []
        for file in os.listdir(backup_dir):
            if file.endswith(".zip"):
                backup_path = os.path.join(backup_dir, file)
                backup_size = os.path.getsize(backup_path) / (1024 * 1024)
                backup_time = datetime.fromtimestamp(os.path.getctime(backup_path))

                backups.append({
                    'name'    : file,
                    'path'    : backup_path,
                    'size'    : f"{backup_size:.2f} MB",
                    'created' : backup_time.strftime("%Y-%m-%d %H:%M")
                })

        return backups


    #--Playtimw update thread--#    
    def update_playtime_thread(self):
        while self.server_process:
            try:
                online_players = self.get_online_players()
                if online_players and not "error" in online_players:
                    for player in online_players:
                        if player.strip():
                            self.update_playtime(player, 1)
            except Exception as e:
                pass
            time.sleep(60)

    #--Spielzeit updaten--#
    def update_playtime(self, player, playtime):
        local_conn = sqlite3.connect(self.db_path)

        try:
            if not local_conn:
                print(translations[config.LANGUAGE]["db_conn_error"])   
                return
            c = local_conn.cursor()
            c.execute("SELECT playtime FROM player_playtime WHERE player = ?", (player.lower(),))
            result = c.fetchone()
            local_conn.commit()
            if result:
                current_playtime = result[0]
                new_playtime = current_playtime + playtime
                c.execute("UPDATE player_playtime SET playtime = ? WHERE player = ?", (new_playtime, player.lower()))
            else:
                c.execute("INSERT INTO player_playtime (player, playtime) VALUES (?, ?)", (player.lower(), playtime))
            local_conn.commit()
        except Exception as e:
            print(f"{translations[config.LANGUAGE]["error"]}: {e}")

    #--Spiezeit auslesen--#
    def get_playtime(self, player):
        try:
            if not self.conn:
                print(translations[config.LANGUAGE]["db_conn_error"])
                return 0
            c = self.conn.cursor()
            c.execute("SELECT playtime FROM player_playtime WHERE player = ?", (player.lower(),))
            self.conn.commit()
            result = c.fetchone()
            if result:
                return result[0]
            else:
                return translations[config.LANGUAGE]["error_playtime"]
        except Exception as e:
            print(f"{translations[config.LANGUAGE]["error"]}: {e}")

    def convert_to_date(self, time):
        timestamp_s = time / 1000
        date = datetime.fromtimestamp(timestamp_s)
        formated_date = date.strftime("%Y-%m-%d %H:%M")
        return formated_date

    #--Alle spieler die online sind auflisten--#
    def get_online_players(self):
        if not self.server_process:
            print(translations[config.LANGUAGE]["not_running"])
            input(translations[config.LANGUAGE]["continur_menu"])
            self.clear_console()
            return ["error"]

        self.server_process.stdin.write("list\n")
        self.server_process.stdin.flush()
        time.sleep(0.4)

        while True:
            output = self.server_process.stdout.readline()
            if "players online" in output.lower():
                players = output.split(": ")[-1].strip().split(", ")
                players = [player.lower() for player in players]
                return players
            if output == '' and self.server_process.poll() is not None:
                break 

        return [] 
    

    def get_player_pos(self, player):
        if not self.server_process:
            print(translations[config.LANGUAGE]["not_running"])
            self.clear_console()
            return ["error"]

        self.server_process.stdin.write(f"data get entity {player}\n")
        self.server_process.stdin.flush()
        time.sleep(0.4)

        while True:
            output = self.server_process.stdout.readline()
            if "entity data" in output.lower():
                try:
                    # Use regex directly on output to extract position data
                    pattern = r'Pos: \[(.*?)\]'
                    match = re.search(pattern, output)
                    if match:
                        pos_str = match.group(1)
                        pos_values = [float(x.strip().replace('d', '')) for x in pos_str.split(',')]
                        return {
                            'x': round(pos_values[0]),
                            'y': round(pos_values[1]),
                            'z': round(pos_values[2])
                        }
                    else:
                        return {
                            'x': '-',
                            'y': '-',
                            'z': '-'
                        }
                except Exception as e:
                    print(f"{translations[config.LANGUAGE]['re_parse_error']}: {e}")
                    return {
                        'x': '-',
                        'y': '-',
                        'z': '-'
                    } 

            if "no entity" in output.lower():
                return {
                    'x': '-',
                    'y': '-',
                    'z': '-'
                } 

            if output == '' and self.server_process.poll() is not None:
                break
    
    #--Alle gebannten spieler auflisten--#
    def get_banned_players(self):
        file = "banned-players.json"
        path = os.path.join(self.server_dir, file)
    
        try:
            with open(path, "r") as f:
                banned_data = json.load(f)

                if isinstance(banned_data, list):
                    banned_players = [player['name'].lower() for player in banned_data]
                else:
                    print(translations[config.LANGUAGE]["json_error"])
                    return translations[config.LANGUAGE]["error"]

            return banned_players

        except FileNotFoundError:
            print(f"{translations[config.LANGUAGE]["not_found_1"]} {path} {translations[config.LANGUAGE]["not_found_2"]}")
            return ""

    #--Whitlist auslesen--#    
    def get_whitelist(self, element):
        file = "whitelist.json"
        path = os.path.join(self.server_dir, file)
        try:
            with open(path, "r") as f:
                whitelist_data = json.load(f)
                if isinstance(whitelist_data, list):
                    info = [data[str(element)].lower() for data in whitelist_data]
                    return info
        except FileNotFoundError:
            print(f"{translations[config.LANGUAGE]["not_found_1"]} {path} {translations[config.LANGUAGE]["not_found_2"]}")

    #spieler info anzeigen--#
    def get_player_info(self, player):
        online_player = self.get_online_players()
        playtime      = self.get_playtime(player)
        last_pos      = self.get_player_pos(player)

        if player.lower() in online_player:
            status = "Online"
        else:
            status = "Offline"

        player_info = {
            'player': player,
            'playtime': playtime,
            'last_pos': last_pos,
            'status': status
        }

        return player_info
    
    #--wlan ssid rausfinden--#
    def get_wlan_ssid(self):
        try:
            result = subprocess.run("iwgetid -r", shell=True, capture_output=True, text=True)
            return result.stdout.strip()
        except Exception:
            return translations[config.LANGUAGE]["ssid_error"]

    #--local ip rausfinden--#
    def get_local_ip(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]

    #--server info anzeigen
    def get_server_info(self):
        wlan_ssid = self.get_wlan_ssid()
        local_ip  = self.get_local_ip()
        status    = "Online" if self.server_process else "Offline"

        print(f"{translations[config.LANGUAGE]["server_status"]}:   {status}")
        print(f"{translations[config.LANGUAGE]["wlan_ssid"]}:       {wlan_ssid}")
        print(f"local IP:           {local_ip}")
        print(f"{translations[config.LANGUAGE]["local_server_ip"]}: {local_ip}:25565")

    #--Spieler bannen--#
    def ban_player(self, player, reason="Banned By operator"):
        self.send_command(f"ban {player} {reason}")
        print(f"{translations[config.LANGUAGE]["bann_1"]} {player} {translations[config.LANGUAGE]["bann_2"]}")
        input(translations[config.LANGUAGE]["continur_menu"])
        self.clear_console()

    #--Spieler Entbannen--#
    def unban_player(self, player):        
        self.send_command(f"pardon {player}")
        print(f"{translations[config.LANGUAGE]["bann_1"]} {player} {translations[config.LANGUAGE]["unban_2"]}")
        input(translations[config.LANGUAGE]["continur_menu"])
        self.clear_console()

    #--Spieler Kicken--#
    def kick_player(self, player, reason="Kickt by an Operator"):
        self.send_command(f"kick {player} {reason}")
        print(f"{translations[config.LANGUAGE]["bann_1"]} {player} {translations[config.LANGUAGE]["kick_2"]}")


manager = MinecraftServer()

while True:
    manager.print_menu()
    choice = input("> ")
    manager.clear_console()

    if choice == "1":
        ram = int(input("RAM (GB): ")) * 1024
        manager.start_server(ram)

    elif choice == "2":
        players = manager.get_online_players()
        if not "error" in players:
            print(f"{translations[config.LANGUAGE]["online_player"]}: " + ", ".join(players))
        input(translations[config.LANGUAGE]["continur_menu"])
        manager.clear_console()

    elif choice == "3":
        player = input(f"{translations[config.LANGUAGE]["playername"]}: ").lower()
        reason = input(f"{translations[config.LANGUAGE]["reason"]}: ")
        manager.ban_player(player, reason)

    elif choice == "4":
        banned_players = manager.get_banned_players()
        print(f"{translations[config.LANGUAGE]["banned_players"]}: ")
        for player in banned_players:
            print(player)
        player = input(f"{translations[config.LANGUAGE]["playername"]}: ").lower()
        manager.unban_player(player)

    elif choice == "5":
        player = input(f"{translations[config.LANGUAGE]["playername"]}: ").lower()
        reason = input(f"{translations[config.LANGUAGE]["reason"]}: ")
        manager.kick_player(player, reason)
        input(translations[config.LANGUAGE]["continur_menu"])
        
    elif choice == "6":
        whitelist_players = manager.get_whitelist("name")
        print(f"{translations[config.LANGUAGE]["whitlist_players"]}: ")
        if whitelist_players:
            for player in whitelist_players:
                print(player)
        else:
            print(translations[config.LANGUAGE]["no_in_whitelist"])
        input(translations[config.LANGUAGE]["continur_menu"])
        manager.clear_console()
    elif choice == "7":
        whitelist_players = manager.get_whitelist("name")
        player = input(f"{translations[config.LANGUAGE]["playername"]}: ").lower()
        if player in whitelist_players:
            player_info = manager.get_player_info(player)
            
            print(f"{translations[config.LANGUAGE]["playername"]}:  {player_info['player']}")
            print(f"{translations[config.LANGUAGE]["playtime"]}:    {player_info['playtime']} min")
            print(f"{translations[config.LANGUAGE]["status"]}:      {player_info['status']}")
            print(f"{translations[config.LANGUAGE]['position']}:    {player_info['last_pos']['x']}, {player_info['last_pos']['y']}, {player_info['last_pos']['z']}")

            input(translations[config.LANGUAGE]["continur_menu"])
            manager.clear_console()

        else:
            print(translations[config.LANGUAGE]["invalid_player"])
            input(translations[config.LANGUAGE]["continur_menu"])
            manager.clear_console()
    
    elif choice == "8":
        manager.stop_server()
        input(translations[config.LANGUAGE]["continur_menu"])
        manager.clear_console()

    elif choice == "9":
        result = manager.create_backup()
        print(result)
        input(translations[config.LANGUAGE]["continur_menu"])
        manager.clear_console()


    elif choice == "10":
        backup_path = input(f"{translations[config.LANGUAGE]["backup_file"]}: ")
        manager.load_backup(backup_path)
        input(translations[config.LANGUAGE]["continur_menu"])
        manager.clear_console()
    
    elif choice == "11":
        manager.get_server_info()
        input(translations[config.LANGUAGE]["continur_menu"])
        manager.clear_console()


