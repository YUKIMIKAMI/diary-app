.PHONY: help install dev build start stop clean test lint format

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install all dependencies
	cd frontend && npm install
	cd backend && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies
	cd frontend && npm install

install-backend: ## Install backend dependencies
	cd backend && pip install -r requirements.txt

dev: ## Start development environment with Docker
	docker-compose up -d
	@echo "Frontend: http://localhost:3000"
	@echo "Backend:  http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

dev-frontend: ## Start frontend development server
	cd frontend && npm run dev

dev-backend: ## Start backend development server
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

build: ## Build Docker images
	docker-compose build

start: ## Start production environment
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

stop: ## Stop all containers
	docker-compose down

clean: ## Clean up containers and volumes
	docker-compose down -v
	rm -rf frontend/node_modules frontend/.next
	rm -rf backend/__pycache__ backend/.pytest_cache

db-migrate: ## Run database migrations
	docker-compose exec backend alembic upgrade head

db-reset: ## Reset database
	docker-compose exec backend alembic downgrade base
	docker-compose exec backend alembic upgrade head

test: ## Run all tests
	cd frontend && npm test
	cd backend && pytest

test-frontend: ## Run frontend tests
	cd frontend && npm test

test-backend: ## Run backend tests
	cd backend && pytest

test-coverage: ## Run tests with coverage
	cd frontend && npm run test:coverage
	cd backend && pytest --cov=app --cov-report=html

lint: ## Run linters
	cd frontend && npm run lint
	cd backend && ruff check . && mypy app

lint-frontend: ## Run frontend linter
	cd frontend && npm run lint

lint-backend: ## Run backend linters
	cd backend && ruff check . && mypy app

format: ## Format code
	cd frontend && npm run format
	cd backend && black . && ruff check --fix .

format-frontend: ## Format frontend code
	cd frontend && npm run format

format-backend: ## Format backend code
	cd backend && black . && ruff check --fix .

type-check: ## Run type checking
	cd frontend && npm run type-check
	cd backend && mypy app

logs: ## Show Docker logs
	docker-compose logs -f

logs-frontend: ## Show frontend logs
	docker-compose logs -f frontend

logs-backend: ## Show backend logs
	docker-compose logs -f backend

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend /bin/sh

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U diary_user -d diary_app