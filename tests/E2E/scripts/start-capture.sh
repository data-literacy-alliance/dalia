#!/usr/bin/env bash
set -e

# Virtual display
Xvfb :99 -screen 0 1280x900x24 -ac &
export DISPLAY=:99
sleep 1

# VNC server (no password, localhost only)
x11vnc -display :99 -forever -nopw -quiet -bg

# noVNC web proxy  → connects to VNC on :5900, serves HTTP on :6080
websockify --web /usr/share/novnc 6080 localhost:5900 &

echo ""
echo "=========================================="
echo " noVNC ready at http://localhost:6080/vnc.html"
echo " Open that URL, then log in to"
echo " https://search.dalia.education"
echo " Press ENTER here when you are logged in."
echo "=========================================="
echo ""

node /app/scripts/capture-session.js
