#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$HOME/online-examination-devops"

sudo apt-get update
sudo apt-get install -y git docker.io docker-compose-plugin

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker "$USER"

if [ ! -d "$PROJECT_DIR/.git" ]; then
  git clone https://github.com/raviprakash-c/online-examination-devops.git "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

cat > .env <<'ENV'
MYSQL_ROOT_PASSWORD=replace-me
MYSQL_USER=examuser
MYSQL_PASSWORD=replace-me
MYSQL_HOST_PORT=3306
BACKEND_HOST_PORT=5000
FRONTEND_HOST_PORT=80
SECRET_KEY=replace-me-with-a-long-random-value
CORS_ORIGINS=http://your-ec2-public-ip
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace-me-with-a-strong-password
ENV

echo "Bootstrap complete."
echo "Edit $PROJECT_DIR/.env before starting the stack."
echo "Then run: docker compose -f docker/docker-compose.yml up -d --build"
