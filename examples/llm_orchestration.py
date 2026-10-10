"""Let a configured LLM plan and synthesize a request using Python specialists.

Run: uv run python -m examples.llm_orchestration 'Count words in these two texts: ...'
The provider must support Chat Completions and JSON mode.
"""

import asyncio
import sys

from src import ExecutionService, Settings, build_llm

from .parallel_plan import build_registry


async def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m examples.llm_orchestration REQUEST")
    settings = Settings()
    async with build_llm(settings) as model:
        result = await ExecutionService.from_model(build_registry(), model, settings).run(
            sys.argv[1]
        )
        print(result.model_dump_json(indent=2))
        if result.status in {"failed", "timed_out"}:
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
