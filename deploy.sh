#!/usr/bin/env bash

set -e

DEPLOY_HOST="${DEPLOY_HOST:-${1:?Usage: ./deploy.sh host [hostname] [repo_url] or DEPLOY_HOST=host SERVER_NAME=hostname REPO_URL=url ./deploy.sh}}"
SERVER_NAME="${SERVER_NAME:-${2:-booty.datashaman.com}}"
DEPLOY_USER="${DEPLOY_USER:-$(whoami)}"
REPO_URL="${REPO_URL:-${3:-git@github.com:datashaman/booty.git}}"
INSTALL_DIR="/opt/booty"
SERVICE_NAME="booty"

ssh "$DEPLOY_HOST" bash -s "$DEPLOY_USER" "$REPO_URL" "$INSTALL_DIR" "$SERVICE_NAME" "$SERVER_NAME" <<'REMOTE'
set -e

DEPLOY_USER="$1"
REPO_URL="$2"
INSTALL_DIR="$3"
SERVICE_NAME="$4"
SERVER_NAME="$5"

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

# Generate nginx config from template
export SERVER_NAME
envsubst '${SERVER_NAME}' < booty.conf > /tmp/booty.conf
sudo cp /tmp/booty.conf /etc/nginx/sites-available/booty.conf
rm /tmp/booty.conf

# Ensure nginx site is enabled
if [ ! -L /etc/nginx/sites-enabled/booty.conf ]; then
    sudo ln -sf /etc/nginx/sites-available/booty.conf /etc/nginx/sites-enabled/booty.conf
fi
sudo nginx -t && sudo systemctl restart nginx

# Ensure that the booty service is enabled and restarted
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# Print the status of the booty service
sudo systemctl status "$SERVICE_NAME"
REMOTE
