#!/bin/bash
# Build "Video Downloader.app" on the Desktop so the app launches with one
# double-click (no Terminal window). macOS only.
#
# Run this AFTER completing the setup steps in the README (venv + deps).
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Desktop/Video Downloader.app"

echo "Building $APP"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# Info.plist
cp "$REPO_DIR/desktop-app/Info.plist" "$APP/Contents/Info.plist"

# launch executable, with this repo's absolute path baked in
sed "s|__APP_DIR__|$REPO_DIR|g" "$REPO_DIR/desktop-app/launch" \
  > "$APP/Contents/MacOS/launch"
chmod +x "$APP/Contents/MacOS/launch"

# App icon (best effort — the app works fine without a custom icon)
if [ -x "$REPO_DIR/.venv/bin/python" ]; then
  "$REPO_DIR/.venv/bin/python" -m pip install --quiet pillow 2>/dev/null || true
  if "$REPO_DIR/.venv/bin/python" "$REPO_DIR/make_icon.py" 2>/dev/null \
     && command -v iconutil >/dev/null; then
    iconutil -c icns /private/tmp/vd_icon.iconset \
      -o "$APP/Contents/Resources/appicon.icns" 2>/dev/null \
      && echo "  icon: built" || echo "  icon: skipped"
  else
    echo "  icon: skipped (Pillow/iconutil unavailable)"
  fi
fi

# Register with LaunchServices so Finder picks up the icon/metadata
touch "$APP"
LSREG="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
[ -x "$LSREG" ] && "$LSREG" -f "$APP" 2>/dev/null || true

echo "Done. Double-click \"Video Downloader\" on your Desktop to launch."
