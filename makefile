# Stop and remove old containers if they exist
down:
	docker compose down

# Force remove any leftover container with the same name
clean:
	-docker rm -f cloudflared || true
	-docker rm -f bajeti_app || true

# Build the app (useful after code changes)
build:
	docker compose build

# Start fresh: remove old, build, then start
up: down clean build
	docker compose up -d

# View logs for cloudflared
logs_cloudflared:
	docker logs -f cloudflared

# Rebuild docker after new deployment
rebuild:
	docker compose down
	docker compose build
	docker compose up -d

# View bajeti logs
logs_bajeti:
	docker logs -f bajeti_app

# Start dev instance
dev:
	docker compose -f docker-compose.dev.yml up --build

# Stop dev instance
stop-dev:
	docker compose -f docker-compose.dev.yml down

# Prune dev
prune-dev:
	docker system prune -af