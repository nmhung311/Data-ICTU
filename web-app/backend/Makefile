# Vietnamese Legal Metadata Extractor - Docker Commands

.PHONY: help build up down dev test clean logs shell

# Default target
help:
	@echo "Vietnamese Legal Metadata Extractor - Docker Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  build     - Build Docker images"
	@echo "  up        - Start production containers"
	@echo "  down      - Stop all containers"
	@echo "  dev       - Start development environment"
	@echo "  test      - Run tests in container"
	@echo "  clean     - Clean up containers and images"
	@echo "  logs      - Show container logs"
	@echo "  shell     - Open shell in container"
	@echo "  restart   - Restart containers"

# Production commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

# Development commands
dev:
	docker-compose -f docker-compose.dev.yml up -d

dev-down:
	docker-compose -f docker-compose.dev.yml down

# Testing
test:
	docker-compose -f docker-compose.dev.yml --profile test run --rm backend-test

# Utility commands
logs:
	docker-compose logs -f backend

shell:
	docker-compose exec backend bash

clean:
	docker-compose down -v
	docker system prune -f

# Quick start
start: build up
	@echo "Vietnamese Legal Metadata Extractor is running!"
	@echo "API: http://localhost:5000"
	@echo "Frontend: http://localhost:3000"

# Development start
dev-start: dev
	@echo "Development environment is running!"
	@echo "API: http://localhost:5001"
