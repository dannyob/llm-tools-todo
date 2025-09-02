.PHONY: help install install-dev test clean build upload upload-test check-version lint format
.DEFAULT_GOAL := help

# Configuration
PYTHON := python
UV := uv
PACKAGE_NAME := llm-tools-todo

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Environment setup
venv: ## Create virtual environment
	$(UV) venv
	@echo "Activate with: source .venv/bin/activate"

install: venv ## Install package in development mode
	source .venv/bin/activate && $(UV) pip install -e .

install-dev: venv ## Install package with development dependencies
	source .venv/bin/activate && $(UV) pip install -e ".[test]"
	source .venv/bin/activate && $(UV) pip install build twine

# Testing
test: ## Run all tests
	source .venv/bin/activate && $(PYTHON) -m pytest tests/ -v

test-coverage: ## Run tests with coverage report
	source .venv/bin/activate && $(UV) pip install coverage
	source .venv/bin/activate && coverage run -m pytest tests/
	source .venv/bin/activate && coverage report
	source .venv/bin/activate && coverage html

# Code quality
lint: ## Run linting (install ruff if needed)
	source .venv/bin/activate && $(UV) pip install ruff
	source .venv/bin/activate && ruff check .

format: ## Format code (install ruff if needed)
	source .venv/bin/activate && $(UV) pip install ruff
	source .venv/bin/activate && ruff format .

lint-fix:
	source .venv/bin/activate && $(UV) pip install ruff
	source .venv/bin/activate && ruff check . --fix

check: lint format test ## Run linting and tests

check-fix: lint-fix format test

# Build and distribution
clean: ## Clean build artifacts and cache files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

build: clean ## Build distribution packages
	source .venv/bin/activate && $(PYTHON) -m build

check-version: ## Check if version needs to be updated for PyPI
	@echo "Current version in pyproject.toml:"
	@grep "version" pyproject.toml
	@echo ""
	@echo "Latest version on PyPI (if package exists):"
	@pip index versions $(PACKAGE_NAME) || echo "Package not found on PyPI (this is normal for new packages)"

# PyPI publishing
upload-test: build ## Upload to TestPyPI
	source .venv/bin/activate && twine check dist/*
	source .venv/bin/activate && twine upload --repository testpypi dist/*
	@echo ""
	@echo "Test installation with:"
	@echo "pip install --index-url https://test.pypi.org/simple/ $(PACKAGE_NAME)"

upload: build ## Upload to PyPI (production)
	source .venv/bin/activate && twine check dist/*
	@echo "About to upload to PyPI. This cannot be undone!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ]
	source .venv/bin/activate && twine upload dist/*

# Development workflow
dev-setup: install-dev ## Complete development setup
	@echo "Development environment ready!"
	@echo "Run 'source .venv/bin/activate' to activate the virtual environment"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make check' to run linting and tests"

# LLM plugin specific
install-plugin: install ## Install plugin and test with LLM
	source .venv/bin/activate && llm install .
	@echo ""
	@echo "Plugin installed! Test with:"
	@echo "llm tools  # Should show Todo tools"
	@echo "llm prompt 'Please start a new todo session' --tool Todo"

uninstall-plugin: ## Uninstall LLM plugin
	source .venv/bin/activate && llm uninstall $(PACKAGE_NAME)

# CI/CD helpers
ci-test: ## Run tests in CI environment
	$(PYTHON) -m pytest tests/ -v --tb=short

ci-build: ## Build for CI (no virtual env)
	$(PYTHON) -m build

# Documentation
docs: ## Generate documentation (placeholder)
	@echo "Documentation target - implement as needed"
	@echo "Consider adding sphinx, mkdocs, or similar"

# Version bumping helpers
version-patch: ## Show how to bump patch version
	@echo "To bump patch version (0.1.0 -> 0.1.1):"
	@echo "  1. Edit pyproject.toml version field"
	@echo "  2. Run 'make check-version' to verify"
	@echo "  3. Run 'make upload-test' to test"
	@echo "  4. Run 'make upload' to publish"

version-minor: ## Show how to bump minor version  
	@echo "To bump minor version (0.1.0 -> 0.2.0):"
	@echo "  1. Edit pyproject.toml version field"
	@echo "  2. Run 'make check-version' to verify"
	@echo "  3. Run 'make upload-test' to test"
	@echo "  4. Run 'make upload' to publish"

# Quick development commands
quick-test: ## Quick test run (no setup)
	source .venv/bin/activate && $(PYTHON) -m pytest tests/ -x

watch-test: ## Watch for changes and run tests
	source .venv/bin/activate && $(UV) pip install pytest-watch
	source .venv/bin/activate && ptw tests/ llm_tools_todo.py
