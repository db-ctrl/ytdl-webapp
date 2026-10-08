"""
Simple local web app to download YouTube videos with yt-dlp.
For personal / educational use only. Runs on localhost.
"""
import os
import re
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, abort
import yt_dlp

BASE_DIR = Path(__file__).resolve().parent
# Auto-save straight into the user's Downloads folder, in a tidy subfolder.
DOWNLOAD_DIR = Path.home() / "Downloads" / "Video Downloader"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _locate_ffmpeg():
    """Find ffmpeg even when launched from Finder (which strips Homebrew from PATH).

    Returns the directory containing ffmpeg, or None if not found. Also ensures
    that directory is on PATH so yt-dlp's own lookups succeed.
    """
    import shutil

    common = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]
    # Make sure common install dirs are visible to this process and yt-dlp.
    parts = os.environ.get("PATH", "").split(os.pathsep)
    for d in common:
        if d not in parts and os.path.isdir(d):
            parts.append(d)
    os.environ["PATH"] = os.pathsep.join(parts)

    found = shutil.which("ffmpeg")
    return str(Path(found).parent) if found else None


FFMPEG_DIR = _locate_ffmpeg()

app = Flask(__name__)

# In-memory job registry: job_id -> dict(status, progress, title, filename, error)
jobs = {}
jobs_lock = threading.Lock()

# Basic sanity check so we only accept plausible video URLs.
URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _set(job_id, **kwargs):
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(kwargs)


def _progress_hook(job_id):
    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            pct = (downloaded / total * 100) if total else None
            _set(
                job_id,
                status="downloading",
                progress=round(pct, 1) if pct is not None else None,
                speed=d.get("_speed_str", "").strip() or None,
                eta=d.get("_eta_str", "").strip() or None,
            )
        elif d["status"] == "finished":
            # Download of one stream done; post-processing (merge/convert) may follow.
            _set(job_id, status="processing", progress=100)
    return hook


def _build_opts(job_id, fmt):
    outtmpl = str(DOWNLOAD_DIR / "%(title)s [%(id)s].%(ext)s")
    opts = {
        "outtmpl": outtmpl,
        "progress_hooks": [_progress_hook(job_id)],
        "noplaylist": True,
        "restrictfilenames": False,
        "quiet": True,
        "no_warnings": True,
    }
    if FFMPEG_DIR:
        opts["ffmpeg_location"] = FFMPEG_DIR
    if fmt == "audio":
        opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
        )
    else:  # video (default): best mp4 up to 1080p, merged
        opts.update(
            {
                "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
                "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "merge_output_format": "mp4",
            }
        )
    return opts


def _run_download(job_id, url, fmt):
    try:
        opts = _build_opts(job_id, fmt)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            _set(job_id, title=info.get("title"))
            # Resolve the actual final filename (after any postprocessing).
            filename = ydl.prepare_filename(info)
            if fmt == "audio":
                filename = str(Path(filename).with_suffix(".mp3"))
            else:
                # merge_output_format forces .mp4 in most cases
                p = Path(filename)
                if not p.exists():
                    mp4 = p.with_suffix(".mp4")
                    if mp4.exists():
                        filename = str(mp4)
            final = Path(filename)
            _set(
                job_id,
                status="done",
                progress=100,
                filename=final.name if final.exists() else None,
            )
    except Exception as e:  # noqa: BLE001 - surface any yt-dlp error to the UI
        _set(job_id, status="error", error=str(e))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    fmt = data.get("format", "video")
    if not URL_RE.match(url):
        return jsonify({"error": "Please enter a valid http(s) URL."}), 400
    if fmt not in ("video", "audio"):
        fmt = "video"

    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {"status": "queued", "progress": 0, "url": url, "format": fmt}
    threading.Thread(target=_run_download, args=(job_id, url, fmt), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    return jsonify(job)


def _ytdlp_version():
    """Version of yt-dlp currently loaded in this running process."""
    try:
        return yt_dlp.version.__version__
    except Exception:  # noqa: BLE001
        return "unknown"


def _ytdlp_version_on_disk():
    """Version installed on disk (may differ from loaded after an update)."""
    try:
        out = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True, text=True, timeout=20,
        )
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def _restart_self():
    """Restart cleanly so updated modules load.

    A plain os.execv would inherit the still-open listening socket and the new
    server would fail to bind ("Address already in use"). Instead we spawn a
    detached helper that waits for THIS process to exit (freeing the port), then
    starts a fresh server. We then exit so the port is released.
    """
    logf = open(BASE_DIR / "server.log", "a")
    subprocess.Popen(
        [sys.executable, str(BASE_DIR / "_restart.py"),
         sys.executable, str(BASE_DIR / "app.py")],
        start_new_session=True,  # survive our exit
        stdout=logf, stderr=subprocess.STDOUT,
    )
    # Give Popen a beat to spawn, then exit so the listening socket closes.
    threading.Timer(0.4, lambda: os._exit(0)).start()


@app.route("/api/version")
def version():
    return jsonify({"yt_dlp": _ytdlp_version()})


@app.route("/api/update", methods=["POST"])
def update():
    # Don't restart out from under an active download.
    with jobs_lock:
        active = any(
            j.get("status") in ("queued", "downloading", "processing")
            for j in jobs.values()
        )
    if active:
        return jsonify({"error": "A download is in progress. Try again when it finishes."}), 409

    old = _ytdlp_version()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "--pre", "yt-dlp[default]"],
            capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Update timed out. Check your internet connection."}), 504
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-400:]
        return jsonify({"error": "Update failed: " + tail}), 500

    new = _ytdlp_version_on_disk()
    changed = new not in (old, "unknown")
    if changed:
        # Restart shortly so the new yt-dlp is actually loaded (this response goes out first).
        threading.Timer(1.0, _restart_self).start()
    return jsonify({"old": old, "new": new, "changed": changed, "restarting": changed})


@app.route("/api/reveal/<job_id>", methods=["POST"])
def reveal(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or not job.get("filename"):
        return jsonify({"error": "nothing to reveal"}), 404
    target = (DOWNLOAD_DIR / job["filename"]).resolve()
    if DOWNLOAD_DIR.resolve() not in target.parents or not target.exists():
        return jsonify({"error": "file not found"}), 404
    # Reveal the saved file in Finder (macOS). Best-effort; ignore failures.
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(target)])
    return jsonify({"ok": True})


@app.route("/files/<path:filename>")
def get_file(filename):
    # Prevent path traversal; only serve files that live in DOWNLOAD_DIR.
    target = (DOWNLOAD_DIR / filename).resolve()
    if DOWNLOAD_DIR.resolve() not in target.parents:
        abort(403)
    if not target.exists():
        abort(404)
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    print("\n  YouTube downloader running at:  http://127.0.0.1:5001\n")
    app.run(host="127.0.0.1", port=5001, debug=False)
