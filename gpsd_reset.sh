#!/bin/bash

echo "Stopping systemd gpsd services..."
sudo systemctl stop gpsd.socket
sudo systemctl stop gpsd

echo "Disabling auto-start..."
sudo systemctl disable gpsd.socket
sudo systemctl disable gpsd

echo "Killing any running gpsd processes..."
sudo killall gpsd 2>/dev/null

echo "Removing stale gpsd sockets..."
sudo rm -f /var/run/gpsd.sock

echo "Starting fresh gpsd instance..."
sudo gpsd /dev/ttyAMA0 -F /var/run/gpsd.sock

echo "Checking if gpsd is running on port 2947..."
sudo lsof -i :2947

echo ""
echo "If you see gpsd listening on 2947, it's working!"
echo "Run 'cgps' in another terminal to view GPS data."
