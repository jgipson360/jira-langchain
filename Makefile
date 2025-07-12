.PHONY: help install test lint format clean

help:
	@echo "Available commands:"
	@echo "  install    Install dependencies"
	@echo "  test       Run tests"
	@echo "  lint       Run linting checks"
	@echo "  format     Format code"
	@echo "  clean      Clean up cache files"

install:
	pip install -r requirements.txt

test:
	pytest

lint:
	black --check --diff .
	isort --check-only --diff .
	flake8 .

format:
	black .
	isort .

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name "coverage.xml" -delete
