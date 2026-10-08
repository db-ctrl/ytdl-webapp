# Video Downloader

A simple local web app that downloads videos (and audio) using
[yt-dlp](https://github.com/yt-dlp/yt-dlp). Built for personal and educational use.

Paste a URL, choose **Video (MP4)** or **Audio (MP3)**, and it downloads with live
progress and auto-saves to `~/Downloads/Video Downloader/`. It runs entirely on
`localhost` — nothing is uploaded anywhere.

## Features

- One-click **Video (MP4)** (best quality up to 1080p, merged with ffmpeg) or **Audio (MP3)** (192 kbps)
- Live progress, speed, and ETA
- Auto-saves to `~/Downloads/Video Downloader/` with a "Show in Finder" button
- Built-in **Update yt-dlp** button that updates and restarts the server (YouTube
  breaks yt-dlp often; this keeps it current without the terminal)
- Works on the 1000+ sites yt-dlp supports, not just YouTube

## Requirements

- Python 3.9+
- System tools (macOS, via [Homebrew](https://brew.sh)):
  ```bash
  brew install ffmpeg   # merges video+audio, converts to MP3
  brew install deno     # JS runtime YouTube requires for signature solving
  ```

## Setup

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade --pre -r requirements.txt
```

## Run

```bash
./start.sh
```

Then open <http://127.0.0.1:5001>.

## Updating yt-dlp

YouTube changes its anti-bot measures frequently and breaks stable yt-dlp releases.
Use the **Update yt-dlp** button in the app, or:

```bash
./.venv/bin/python -m pip install --upgrade --pre "yt-dlp[default]"
```

## Notes

- `make_icon.py` generates a macOS `.icns` app icon (requires Pillow).
- Please only download content you have the rights to.

## Disclaimer

This is a personal/educational wrapper around yt-dlp. You are responsible for
complying with the terms of service of any site you use it with and with
applicable copyright law.
