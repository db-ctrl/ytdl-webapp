#!/bin/bash
# Start the local video downloader web app.
cd "$(dirname "$0")"
exec ./.venv/bin/python app.py
