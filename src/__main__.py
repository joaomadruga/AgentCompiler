"""CLI entry point using an application-supplied ExecutionService factory."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import inspect
from contextlib import AsyncExitStack
from pathlib import Path

from .core.tracing import TraceRecorder
from .services.execution_service import ExecutionService


async def execute(args: argparse.Namespace) -> int:
    module_name, separator, factory_name = args.factory.partition(":")
    if not separator or not module_name or not factory_name:
        raise ValueError("Factory must use module:function syntax.")
    factory = getattr(importlib.import_module(module_name), factory_name)
    async with AsyncExitStack() as stack:
        service = factory()
        if inspect.isawaitable(service):
            service = await service
        if hasattr(service, "__aenter__") and hasattr(service, "__aexit__"):
            service = await stack.enter_async_context(service)
        if not isinstance(service, ExecutionService):
            raise TypeError("Factory must return or yield an ExecutionService.")
        trace = TraceRecorder()
        result = await service.run(args.request, trace=trace)
        serialized = result.model_dump_json(indent=2)
        if args.output:
            Path(args.output).write_text(serialized + "\n", encoding="utf-8")
        else:
            print(serialized)
        if args.trace:
            trace.write_jsonl(args.trace)
        return 0 if result.status == "completed" else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute a request with AgentCompiler.")
    parser.add_argument("request", help="Request to plan, execute, and synthesize.")
    parser.add_argument(
        "--factory", required=True, help="Importable module:function service factory."
    )
    parser.add_argument("--output", help="Write the JSON report to this path instead of stdout.")
    parser.add_argument("--trace", help="Write execution events to a JSONL file.")
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(execute(args)))
    except (ValueError, TypeError, ImportError, AttributeError) as error:
        parser.exit(2, f"Configuration error: {error}\n")


if __name__ == "__main__":
    main()
