#!/bin/bash
# Masaad Estimator OCI Deployment Script

# 1. Update and Install Docker
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 2. Setup Project Environment
mkdir -p ~/masaad-estimator/data/postgres
cd ~/masaad-estimator

# 3. Create Docker Compose for OCI
cat <<EOF > docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: masaad_admin
      POSTGRES_PASSWORD: ${DB_PASSWORD:-change_me_now}
      POSTGRES_DB: masaad_db
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://masaad_admin:${DB_PASSWORD:-change_me_now}@db:5432/masaad_db
      LME_API_KEY: \${LME_API_KEY}
    depends_on:
      - db

  frontend:
    build:
      context: ./frontend
    ports:
      - "80:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://YOUR_INSTANCE_IP:8000
EOF

echo "Deployment environment ready. Please clone your repo and run: sudo docker compose up -d"
