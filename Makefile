.PHONY: help install install-skill clean format test

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the package in editable mode
	pip install -e .

install-skill: ## Install or update the Agent SKILL locally
	mkdir -p ~/.agent/skills/blogger-agent
	cp SKILL.md ~/.agent/skills/blogger-agent/SKILL.md
	@echo "✅ Skill successfully installed/updated in ~/.agent/skills/blogger-agent/"

clean: ## Clean up Python cache and build files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf build/
	rm -rf dist/
	@echo "✅ Cleanup complete."

format: ## Format code (placeholder for future tools like black/ruff)
	@echo "⚠️ Formatting tools not yet configured. Recommend adding ruff or black."

test: ## Run tests (placeholder)
	@echo "⚠️ Tests not yet configured."
