.PHONY: help install dev test lint format build run clean

help:
	@echo "Available commands:"
	@echo "  install    - Install Python dependencies"
	@echo "  dev        - Run development server with hot reload"
	@echo "  test       - Run tests with pytest"
	@echo "  lint       - Run linting (ruff, mypy)"
	@echo "  format     - Format code with ruff"
	@echo "  build      - Build Docker image"
	@echo "  run        - Run production server with gunicorn"
	@echo "  docker-up  - Start docker-compose services"
	@echo "  docker-down- Stop docker-compose services"
	@echo "  clean      - Clean up build artifacts"

install:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e ".[dev]" 2>/dev/null || true

dev:
	FLASK_ENV=development python app.py

test:
	pytest -v --tb=short

test-cov:
	pytest --cov=estimator --cov=app --cov-report=term-missing

lint:
	ruff check .
	mypy --ignore-missing-imports .

format:
	ruff check --fix .
	ruff format .

build:
	docker build -t judith-estimator .

run:
	gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 60 app:app

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage 2>/dev/null || true