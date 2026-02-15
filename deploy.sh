#!/usr/bin/env bash

set -e

DEPLOY_USER="${DEPLOY_USER:-$(whoami)}"
REPO_URL="git@github.com:datashaman/booty.git"
INSTALL_DIR="/opt/booty"
SERVICE_NAME="booty"

# Go into opt folder
cd /opt

# Checkout repo into booty folder, only if it doesn't exist
if [ ! -d "$INSTALL_DIR" ]; then
    git clone "$REPO_URL" booty
    sudo chown -R "$DEPLOY_USER:www-data" "$INSTALL_DIR"
fi

# Go into the booty folder and pull the latest changes
cd "$INSTALL_DIR"
git pull

# Create venv only if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Install in edit mode
.venv/bin/pip install -e .

# Ensure that the booty service is enabled and restarted
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# Print the status of the booty service
sudo systemctl status "$SERVICE_NAME"

# Ensure the nginx configuration is in place and nginx is restarted
sudo cp booty.conf /etc/nginx/sites-available/booty.conf
if [ ! -L /etc/nginx/sites-enabled/booty.conf ]; then
    sudo ln -sf /etc/nginx/sites-available/booty.conf /etc/nginx/sites-enabled/booty.conf
fi
sudo nginx -t && sudo systemctl restart nginx
