.PHONY: install check lint test demo

install:
	uv sync

check:
	uv run python -m compileall -q src examples
	uv run ruff check src examples
	git diff --check

lint:
	uv run ruff check src examples

test:
	uv run pytest

demo:
	uv run python -m examples.parallel_plan
