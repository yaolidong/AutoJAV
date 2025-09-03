#!/bin/bash
export DISPLAY=:1
USER=root

# Set VNC password
if [ -n "$VNC_PASSWORD" ]; then
    mkdir -p /root/.vnc
    echo "$VNC_PASSWORD" | vncpasswd -f > /root/.vnc/passwd
    chmod 600 /root/.vnc/passwd
else
    echo "VNC_PASSWORD not set, using default 'password'"
    mkdir -p /root/.vnc
    echo "password" | vncpasswd -f > /root/.vnc/passwd
    chmod 600 /root/.vnc/passwd
fi

# Start VNC server
vncserver $DISPLAY -depth 24 -geometry 1280x800 -localhost no -fg &> /var/log/vncserver.log &

# Start noVNC
/opt/novnc/utils/launch.sh --vnc localhost:5901 --listen 6901 &> /var/log/novnc.log &

# Start window manager
xfce4-session &> /var/log/xfce4-session.log &
