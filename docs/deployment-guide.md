Perfect — that’s a great setup for a personal full-stack deployment workflow using your MacBook as dev, GitHub as the source of truth, and Raspberry Pi as your production/staging host.

Let’s design this properly with a runbook + lightweight CI/CD that makes it repeatable, safe, and mostly automatic — without relying on any paid services.

🧭 Overview of What We’ll Build

You currently:

Develop locally (uvicorn main:app --reload on Mac)

Push to GitHub

SSH into the Pi → git pull origin main → docker build → docker run

We’ll make that cleaner by introducing:

A runbook (documentation + repeatable script)

A Dockerfile (already exists, we’ll refine it)

A GitHub Actions CI/CD pipeline that:

Runs tests & builds the Docker image

Pushes the image to GitHub Container Registry

SSHes into your Raspberry Pi and redeploys automatically

🧱 1. Define a Runbook

Here’s a concise but professional runbook you can put in docs/DEPLOYMENT-RUNBOOK.md:

🧩 Bajeti Deployment Runbook (Raspberry Pi)
Environments

Development: Local (MacBook, using uvicorn main:app --reload)

Production: Raspberry Pi (ssh joshuamangi@192.168.1.120)

Prerequisites

Raspberry Pi has:

Docker & Docker Compose installed

Access to git, python3, node

GitHub repository connected with Raspberry Pi via SSH keys

Environment Variables
Variable Example Description
ENVIRONMENT production Deployment environment
SECRET_KEY <generated> JWT signing key
ALGORITHM HS256 JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES 30 Token expiry duration

These live in .env on both dev and production.

🔨 Deployment Procedure
Option 1: Manual (fallback)
ssh joshuamangi@192.168.1.120
cd ~/bajeti
git pull origin main
docker compose down
docker compose build --no-cache
docker compose up -d

Option 2: Automated via GitHub Actions (preferred)

Commit and push code from your MacBook:

git add .
git commit -m "Update Bajeti"
git push origin main

GitHub Actions will:

Build and test the Docker image

Push it to GitHub Container Registry

SSH into your Raspberry Pi

Pull and restart the container automatically

Logs will appear in your repo’s Actions tab.

⚙️ 2. Update Dockerfile (Pi-compatible)

Your Raspberry Pi likely uses ARM64, so ensure the Dockerfile works across platforms.

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y nodejs npm build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build static assets

RUN npm install --omit=dev && ENVIRONMENT=production node scripts/build.js

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

✅ Works for ARM (Raspberry Pi) and x86 (Mac).

🧰 3. Create docker-compose.yml

This simplifies rebuilds:

version: "3.8"

services:
  bajeti:
    build: .
    container_name: bajeti
    env_file: .env
    ports:
      - "8000:8000"
    restart: always
    volumes:
      - ./app/static:/app/app/static
      - ./app/templates:/app/app/templates

Now you can deploy manually with:

docker compose up -d --build

🚀 4. Add CI/CD with GitHub Actions

Create a workflow file at .github/workflows/deploy.yml:

name: Deploy to Raspberry Pi

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up QEMU (for ARM build)
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v6
        with:
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/bajeti:latest
          platforms: linux/arm64,linux/amd64

      - name: Deploy to Raspberry Pi via SSH
        uses: appleboy/ssh-action@v1.2.0
        with:
          host: 192.168.1.120
          username: joshuamangi
          key: ${{ secrets.PI_SSH_KEY }}
          script: |
            cd ~/bajeti
            git pull origin main
            docker compose down
            docker pull ghcr.io/${{ github.repository_owner }}/bajeti:latest
            docker compose up -d

🔐 5. Set Up GitHub Secrets

In your repo settings → Secrets and variables → Actions → Add:

Secret Description
PI_SSH_KEY Private SSH key that can connect to your Raspberry Pi (~/.ssh/id_rsa from your Mac)
GITHUB_TOKEN Provided automatically by GitHub, don’t change it

✅ You must ensure the public key (~/.ssh/id_rsa.pub) is in your Pi’s ~/.ssh/authorized_keys.

🧩 6. On Your Raspberry Pi (One-time Setup)

Run once:

# Clone the repo

git clone <git@github.com>:yourusername/bajeti.git
cd bajeti

# Copy your .env

cp .env.example .env

# Build and start

docker compose up -d

After that, all deployments will be automatic from GitHub.

⚡ 7. Local Development (Mac)

Keep using:

uvicorn main:app --reload

And occasionally test production image locally:

docker compose up --build

✅ Summary of the Setup
Component Purpose
.env Defines environment (development or production)
Dockerfile Builds a consistent image for both Mac and Pi
docker-compose.yml Simplifies local/remote container management
deploy.yml (GitHub Actions) CI/CD pipeline that builds + deploys automatically
DEPLOYMENT-RUNBOOK.md Documentation for manual fallback and clarity

Would you like me to include a versioned static asset build step in this CI/CD pipeline — so each deployment automatically cache-busts JS/CSS (e.g., main.20251024.js)? It integrates beautifully with your esbuild step and Jinja templates.

🔐 5. Set Up GitHub Secrets

In your repo settings → Secrets and variables → Actions → Add:

Secret Description
PI_SSH_KEY Private SSH key that can connect to your Raspberry Pi (~/.ssh/id_rsa from your Mac)
GITHUB_TOKEN Provided automatically by GitHub, don’t change it

✅ You must ensure the public key (~/.ssh/id_rsa.pub) is in your Pi’s ~/.ssh/authorized_keys.
