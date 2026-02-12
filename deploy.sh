#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="opc-backend"
NGINX_SITE="opc-frontend"
APP_USER="${SUDO_USER:-$USER}"
APP_GROUP="$(id -gn "$APP_USER")"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "==> Deploying One Person Company from: ${PROJECT_DIR}"

if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
  echo "ERROR: ${PROJECT_DIR}/.env not found. Create it before deploy."
  exit 1
fi

echo "==> Ensuring virtualenv + dependencies"
if [[ ! -d "${PROJECT_DIR}/venv" ]]; then
  "${PYTHON_BIN}" -m venv "${PROJECT_DIR}/venv"
fi

source "${PROJECT_DIR}/venv/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "${PROJECT_DIR}/requirements.txt"

BACKEND_PYTHON="${PROJECT_DIR}/venv/bin/python"

echo "==> Writing systemd unit: ${SERVICE_NAME}"
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null <<EOF
[Unit]
Description=One Person Company Backend Engine
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${BACKEND_PYTHON} ${PROJECT_DIR}/workers/engine.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "==> Configuring Nginx site: ${NGINX_SITE}"
sudo tee "/etc/nginx/sites-available/${NGINX_SITE}" > /dev/null <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    root ${PROJECT_DIR};
    index dashboard.html;

    location / {
        try_files \$uri \$uri/ /dashboard.html;
    }
}
EOF

sudo ln -sf "/etc/nginx/sites-available/${NGINX_SITE}" "/etc/nginx/sites-enabled/${NGINX_SITE}"
if [[ -e /etc/nginx/sites-enabled/default ]]; then
  sudo rm -f /etc/nginx/sites-enabled/default
fi

echo "==> Restarting services"
sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"
sudo systemctl enable --now nginx
sudo nginx -t
sudo systemctl reload nginx

echo
echo "Deployment complete."
echo "Backend status:"
sudo systemctl --no-pager --full status "${SERVICE_NAME}" | sed -n '1,12p'
echo
echo "Frontend URL: http://<your-vps-ip>/dashboard.html"
echo "Backend logs: journalctl -u ${SERVICE_NAME} -f"
