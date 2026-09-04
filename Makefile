.PHONY: up down logs build test backend-test frontend-test seed migrate

up:
	docker-compose up -d --build

down:
	docker-compose down

logs:
	docker-compose logs -f

build:
	docker-compose build

backend-test:
	cd backend && python -m pytest -q

frontend-test:
	cd frontend && npm test -- --passWithNoTests

test: backend-test frontend-test

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python seed.py

health:
	curl -s http://localhost:8000/health | python -m json.tool
	curl -s http://localhost:8000/models | python -m json.tool

ps:
	docker-compose ps
