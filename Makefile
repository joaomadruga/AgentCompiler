.PHONY: install check lint test

install:
	uv sync

check:
	uv run python -m compileall -q src benchmark
	uv run ruff check src benchmark
	git diff --check

lint:
	uv run ruff check src benchmark

test:
	uv run pytest
