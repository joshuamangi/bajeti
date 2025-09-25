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
logs:
	docker compose logs -f cloudflared
