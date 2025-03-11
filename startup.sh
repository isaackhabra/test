#!/bin/bash
wget -O /home/e1-target/server.py "https://raw.githubusercontent.com/isaackhabra/test/refs/heads/main/server.py"
python -m venv /home/e1-target/v
python /home/e1-target/server.py
