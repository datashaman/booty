#!/usr/bin/env bash

set -e

DEPLOY_HOST="${DEPLOY_HOST:-${1:?Usage: ./deploy.sh host [hostname] [repo_url] or DEPLOY_HOST=host SERVER_NAME=hostname REPO_URL=url ./deploy.sh}}"
DEPLOY_PORT="${DEPLOY_PORT:-}"
SERVER_NAME="${SERVER_NAME:-${2:-booty.datashaman.com}}"
DEPLOY_USER="${DEPLOY_USER:-$(whoami)}"
REPO_URL="${REPO_URL:-${3:-git@github.com:datashaman/booty.git}}"
INSTALL_DIR="/opt/booty"
SERVICE_NAME="booty"

SSH_OPTS=(-o ConnectTimeout=60 -o ServerAliveInterval=15 -o ServerAliveCountMax=4)
[ -n "$DEPLOY_PORT" ] && SSH_OPTS+=(-p "$DEPLOY_PORT")
SSH_TARGET="${DEPLOY_USER:+${DEPLOY_USER}@}${DEPLOY_HOST}"

ssh "${SSH_OPTS[@]}" "$SSH_TARGET" bash -s "$DEPLOY_USER" "$REPO_URL" "$INSTALL_DIR" "$SERVICE_NAME" "$SERVER_NAME" <<'REMOTE'
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
    sudo mkdir -p "$INSTALL_DIR"
    sudo chown "$DEPLOY_USER:www-data" "$INSTALL_DIR"
    sudo chmod g+w "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
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
envsubst '${SERVER_NAME}' < deploy/booty.conf > /tmp/booty.conf
sudo cp /tmp/booty.conf /etc/nginx/sites-available/booty.conf
rm /tmp/booty.conf

# Ensure nginx site is enabled
if [ ! -L /etc/nginx/sites-enabled/booty.conf ]; then
    sudo ln -sf /etc/nginx/sites-available/booty.conf /etc/nginx/sites-enabled/booty.conf
fi
sudo nginx -t && sudo systemctl restart nginx

# Deploy systemd service
export INSTALL_DIR
envsubst '${INSTALL_DIR}' < deploy/booty.service > /tmp/booty.service
sudo cp /tmp/booty.service "/etc/systemd/system/${SERVICE_NAME}.service"
rm /tmp/booty.service
sudo systemctl daemon-reload

# Create /etc/booty and write release.env for Sentry correlation
sudo mkdir -p /etc/booty
printf 'SENTRY_RELEASE=%s\nSENTRY_ENVIRONMENT=production\n' "$(git rev-parse HEAD)" | sudo tee /etc/booty/release.env > /dev/null

# Ensure that the booty service is enabled and restarted
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# Print the status of the booty service
sudo systemctl status "$SERVICE_NAME"
REMOTE
