"""Detached restart helper.

Started by app.py just before it exits. Waits until the old server has released
port 5001, then launches a fresh server (which loads the just-updated yt-dlp).

Usage: python _restart.py <python_exe> <app.py path>
"""
import os
import socket
import sys
import time

PORT = 5001
py, app_path = sys.argv[1], sys.argv[2]

# Wait (up to ~20s) for the old process to exit and free the port.
for _ in range(100):
    s = socket.socket()
    free = s.connect_ex(("127.0.0.1", PORT)) != 0
    s.close()
    if free:
        break
    time.sleep(0.2)

os.execv(py, [py, app_path])
