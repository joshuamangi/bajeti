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

# Remove any leftover containers (ignore errors). Never prunes volumes or images.
clean:
	@docker rm -f cloudflared bajeti_app 2>/dev/null || true

# Build containers for the selected environment
build:
ifeq ($(ENV),dev)
	@docker compose -f docker-compose.dev.yml build --no-cache
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

# Safe rebuild of the app layer: build, start, migrate, wait until it answers.
# Never prunes anything and never touches the database file or any volume.
rebuild:
	@docker compose build
	@docker compose up -d
	@docker compose exec -T bajeti_app alembic upgrade head
	@for i in $$(seq 1 30); do \
	  if curl -fsS -o /dev/null http://127.0.0.1:8000/; then echo "healthy"; exit 0; fi; \
	  sleep 2; \
	done; echo "NOT healthy after 60 s"; docker compose logs --tail=30 bajeti_app; exit 1

# ---------------------------------------
# 🧑‍💻 Development Commands
# ---------------------------------------

# Start dev environment (FastAPI + esbuild)
dev: test
	@docker compose -f docker-compose.dev.yml up --build

# Stop dev environment
stop-dev:
	@docker compose -f docker-compose.dev.yml down

ENV ?= prod

# make test ENV=dev
ifeq ($(ENV),dev)
	DOCKER_COMPOSE_CMD = docker compose -f docker-compose.dev.yml
else
	DOCKER_COMPOSE_CMD = docker compose
endif

test:
	pytest -q

# Run tests in Docker (if you really need it)
test-docker:
	docker compose -f docker-compose.dev.yml run --rm tests

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
