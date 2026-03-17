.PHONY: run test lint format clean help setup

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies
	pip install -r requirements.txt

run: ## Run the app
	python main.py

test: ## Run tests
	python -m pytest tests/ -v

lint: ## Run ruff linter
	ruff check main.py tests/

format: ## Auto-format code
	ruff format main.py tests/

clean: ## Clean generated files
	rm -rf __pycache__ tests/__pycache__ .pytest_cache htmlcov .ruff_cache
	rm -f data/skills.db
