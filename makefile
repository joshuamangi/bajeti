.PHONY: up down build logs restart

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f cloudflared

restart: down build up
