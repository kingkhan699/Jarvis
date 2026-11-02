#!/data/data/com.termux/files/usr/bin/bash
# Starts the Jarvis voice server inside your Ubuntu box. Leave this window open.
termux-wake-lock 2>/dev/null
echo "Starting the Jarvis voice. Keep this window open. Press CTRL+C to stop."
proot-distro login ubuntu -- bash -c 'cd /root/OpenJarvis && UV_LINK_MODE=copy .venv/bin/python jarvis_voice_server.py'
