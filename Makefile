.PHONY: help install setup run test clean verify

help:
	@echo "Video Hosting Platform - Available Commands"
	@echo "============================================"
	@echo "make install    - Install dependencies"
	@echo "make setup      - Initial setup (create .env, init db)"
	@echo "make verify     - Verify setup is correct"
	@echo "make run        - Run the development server"
	@echo "make worker     - Run Celery worker"
	@echo "make test       - Run test suite"
	@echo "make test-cov   - Run tests with coverage report"
	@echo "make clean      - Clean up generated files"
	@echo "make init-db    - Initialize database"
	@echo "make drop-db    - Drop all database tables"

install:
	pip install -r requirements.txt

setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file. Please edit it with your configuration."; \
	else \
		echo ".env file already exists."; \
	fi
	@mkdir -p uploads/videos uploads/thumbnails logs
	@echo "Setup complete. Run 'make verify' to check installation."

verify:
	python verify_setup.py

run:
	python run.py

worker:
	celery -A celery_worker.celery worker --loglevel=info

test:
	pytest

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

init-db:
	flask init-db

drop-db:
	flask drop-db

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".hypothesis" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/
	rm -f .coverage
	rm -f *.db
	@echo "Cleaned up generated files."
