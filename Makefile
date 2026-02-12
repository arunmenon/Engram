.PHONY: dev test lint format clean docker-up docker-down unit integration infra-test

# Development setup
dev:
	python -m pip install -e ".[dev]"
	pre-commit install

# Run all tests
test: unit

# Unit tests only (no docker required)
unit:
	pytest tests/unit -v --tb=short

# Integration tests (require docker services)
integration: docker-up
	pytest tests/integration -v --tb=short -m integration

# Infrastructure validation tests (require docker services)
infra-test: docker-up
	pytest tests/infra -v --tb=short -m infra

# Linting
lint:
	ruff check src/ tests/
	ruff format --check src/ tests/
	mypy src/context_graph/

# Auto-format
format:
	ruff check --fix src/ tests/
	ruff format src/ tests/

# Docker
docker-up:
	docker compose -f docker/docker-compose.yml up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5

docker-down:
	docker compose -f docker/docker-compose.yml down

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/
