# ---------------------------------------
# 🧱 Docker Compose Shortcuts for Bajeti
# ---------------------------------------

# Default environment
ENV ?= prod

# ---------------------------------------
# 🧩 General Commands
# ---------------------------------------

# Stop and remove all containers
down:
	@docker compose down

# Remove any leftover containers (ignore errors)
clean:
	@docker rm -f cloudflared bajeti_app 2>/dev/null || true
	@docker volume prune -f

# Build containers for the selected environment
build:
ifeq ($(ENV),dev)
	@docker compose -f docker-compose.dev.yml build
else
	@docker compose build
endif

# Start containers
up:
ifeq ($(ENV),dev)
	@docker compose -f docker-compose.dev.yml up --build
else
	@docker compose up -d
endif

# Full rebuild and restart
rebuild: down clean build up

# Stop all containers and remove unused resources
prune:
	@docker system prune -af --volumes

# ---------------------------------------
# 🧑‍💻 Development Commands
# ---------------------------------------

# Start dev environment (FastAPI + esbuild)
dev:
	@docker compose -f docker-compose.dev.yml up --build

# Stop dev environment
stop-dev:
	@docker compose -f docker-compose.dev.yml down

# Clean dev containers and images
prune-dev:
	@docker system prune -af

# ---------------------------------------
# 🚀 Production Commands
# ---------------------------------------

# Deploy production version (used on Raspberry Pi)
deploy: down clean
	@echo "🔧 Building esbuild static assets..."
	@npm run build || echo "⚠️ Skipping esbuild if not installed"
	@echo "📦 Building production Docker image..."
	@docker compose build
	@echo "🚀 Starting Bajeti app..."
	@docker compose up -d

# ---------------------------------------
# 📜 Logs
# ---------------------------------------

logs:
	@docker compose logs -f

logs-bajeti:
	@docker logs -f bajeti_app

logs-cloudflared:
	@docker logs -f cloudflared
