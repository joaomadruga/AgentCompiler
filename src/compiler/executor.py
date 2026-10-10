"""Per-task contract validation, bounded retries, and asynchronous invocation."""

from __future__ import annotations

import asyncio
import json
import time
from copy import deepcopy

from pydantic import JsonValue, TypeAdapter

from ..agents.base import AgentExecutionError, serialize_output
from ..agents.context import AgentContext, ExecutionContext
from ..agents.registry import AgentRegistry
from .schemas import Task, TaskResult, TaskStatus
from .type_system import validate_input_model, validate_json_type
from .validation import reference_input_types, resolve_inputs, validate_value


class TaskExecutor:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    async def execute(self, task: Task, context: ExecutionContext) -> TaskResult:
        spec = self.registry.spec(task.agent_id)
        agent = self.registry.get(task.agent_id)
        local = AgentContext(run=context, task_id=task.id)
        started = time.monotonic()
        attempts = 0
        try:
            inputs = resolve_inputs(task, context.results)
            if spec.input_model is not None:
                inputs = validate_input_model(
                    spec.input_model,
                    inputs,
                    reference_input_types(task, self.registry, context.results),
                )
            else:
                validate_value(inputs, spec.input_schema, "Agent inputs")
            timeout = context.settings.task_timeout_seconds
            async with asyncio.timeout(timeout):
                limit = context.settings.max_task_attempts if spec.retry_safe else 1
                for attempt in range(1, limit + 1):
                    attempts = attempt
                    context.agent_executions += 1
                    local.emit("task_attempt", attempt=attempt, agent_id=task.agent_id)
                    try:
                        # Every retry receives its own input object.
                        if spec.concurrent:
                            output = await agent.run(task.instruction, deepcopy(inputs), local)
                        else:
                            async with self.registry.lock(task.agent_id):
                                output = await agent.run(task.instruction, deepcopy(inputs), local)
                        output = serialize_output(output)
                        if spec.output_model is not None:
                            output = serialize_output(validate_json_type(spec.output_model, output))
                        output = TypeAdapter(JsonValue).validate_python(output)
                        json.dumps(output, allow_nan=False)
                        validate_value(output, spec.output_schema, "Agent output")
                        result = TaskResult(
                            task_id=task.id,
                            agent_id=task.agent_id,
                            status=TaskStatus.SUCCEEDED,
                            output=output,
                            attempts=attempts,
                            duration_seconds=time.monotonic() - started,
                            usage=local.usage,
                        )
                        local.emit(
                            "task_succeeded",
                            attempts=attempts,
                            duration_seconds=result.duration_seconds,
                        )
                        return result
                    except AgentExecutionError as error:
                        if not error.retryable or attempt == limit:
                            raise
                        local.emit("task_retry", attempt=attempt)
                        await asyncio.sleep(
                            context.settings.retry_backoff_seconds * 2 ** (attempt - 1)
                        )
        except asyncio.CancelledError:
            context.results[task.id] = TaskResult(
                task_id=task.id,
                agent_id=task.agent_id,
                status=TaskStatus.CANCELLED,
                error="Task cancelled; external effects may already have occurred.",
                attempts=attempts,
                duration_seconds=time.monotonic() - started,
                usage=local.usage,
            )
            local.emit("task_cancelled")
            raise
        except Exception as error:
            result = TaskResult(
                task_id=task.id,
                agent_id=task.agent_id,
                status=TaskStatus.FAILED,
                error=f"{type(error).__name__}: {error}",
                attempts=attempts,
                duration_seconds=time.monotonic() - started,
                usage=local.usage,
            )
            local.emit("task_failed", error_type=type(error).__name__, attempts=attempts)
            return result
        raise RuntimeError("Task execution ended without a result.")
