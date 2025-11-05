.PHONY: help install install-dev run dev test test-cov test-verbose clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install production and development dependencies"
	@echo "  make install-prod - Install production dependencies"
	@echo "  make run          - Run the API server"
	@echo "  make dev          - Run the API server in development mode (with reload)"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make test-verbose - Run tests in verbose mode"
	@echo "  make clean        - Clean Python cache files"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

install-prod:
	pip install -r requirements.txt

run:
	uvicorn main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest

test-cov:
	pytest --cov=src --cov=main --cov-report=html --cov-report=term

test-verbose:
	pytest -v

clean:
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

