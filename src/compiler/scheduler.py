"""Event-driven DAG scheduling without layer-wide barriers."""

from __future__ import annotations

import asyncio
import time

from ..agents.context import ExecutionContext
from ..agents.registry import AgentRegistry
from .executor import TaskExecutor
from .schemas import CompiledPlan, ExecutionReport, TaskResult, TaskStatus, Usage
from .validation import resolve_reference, topological_order


class Scheduler:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry
        self.executor = TaskExecutor(registry)

    async def run(self, compiled: CompiledPlan, context: ExecutionContext) -> ExecutionReport:
        started = time.monotonic()
        plan = compiled.plan
        tasks = {task.id: task for task in plan.tasks}
        order = topological_order(plan)
        rank = {task_id: index for index, task_id in enumerate(order)}
        priorities: dict[str, float] = {}
        successors: dict[str, list[str]] = {task_id: [] for task_id in tasks}
        for task in plan.tasks:
            for dependency in task.dependency_ids() & tasks.keys():
                successors[dependency].append(task.id)
        for task_id in reversed(order):
            duration = self.registry.spec(tasks[task_id].agent_id).estimated_duration_seconds
            priorities[task_id] = duration + max(
                (priorities[child] for child in successors[task_id]), default=0.0
            )
        pending = set(tasks)
        running: dict[asyncio.Task, str] = {}
        busy_agents: set[str] = set()
        try:
            while pending or running:
                ready = []
                for task_id in sorted(pending, key=rank.get):
                    dependencies = tasks[task_id].dependency_ids()
                    failed = [
                        dep
                        for dep in dependencies
                        if dep in context.results
                        and context.results[dep].status != TaskStatus.SUCCEEDED
                    ]
                    if failed:
                        context.results[task_id] = TaskResult(
                            task_id=task_id,
                            agent_id=tasks[task_id].agent_id,
                            status=TaskStatus.BLOCKED,
                            error=f"Unsuccessful dependencies: {sorted(failed)}",
                        )
                        pending.remove(task_id)
                        context.emit("task_blocked", task_id, dependencies=sorted(failed))
                    elif dependencies.issubset(context.results):
                        ready.append(task_id)
                if context.settings.scheduling == "critical_path":
                    ready.sort(key=lambda task_id: (-priorities[task_id], rank[task_id]))
                for task_id in ready:
                    if len(running) >= context.settings.max_concurrency:
                        break
                    task = tasks[task_id]
                    if task.agent_id in busy_agents:
                        continue
                    if not self.registry.spec(task.agent_id).concurrent:
                        busy_agents.add(task.agent_id)
                    pending.remove(task_id)
                    context.emit("task_started", task_id, agent_id=task.agent_id)
                    future = asyncio.create_task(
                        self.executor.execute(task, context), name=f"agentcompiler:{task_id}"
                    )
                    running[future] = task_id
                if not running:
                    if pending:
                        raise RuntimeError("No runnable tasks remain; unresolved dependencies.")
                    break
                done, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
                for future in sorted(done, key=lambda item: rank[running[item]]):
                    task_id = running.pop(future)
                    busy_agents.discard(tasks[task_id].agent_id)
                    context.results[task_id] = future.result()
        finally:
            for future in running:
                future.cancel()
            if running:
                await asyncio.gather(*running, return_exceptions=True)
            for future, task_id in running.items():
                if not future.cancelled() and future.exception() is None:
                    context.results[task_id] = future.result()
            for task_id in pending:
                context.results[task_id] = TaskResult(
                    task_id=task_id,
                    agent_id=tasks[task_id].agent_id,
                    status=TaskStatus.CANCELLED,
                    error="Execution ended before task dispatch.",
                )
            for alias, target in compiled.aliases.items():
                original = context.results[target]
                result = original.model_copy(deep=True)
                result.task_id = alias
                result.reused_from = target
                result.attempts = 0
                result.duration_seconds = 0
                result.usage = Usage()
                context.results[alias] = result
                context.emit("task_reused", alias, source_task_id=target)
        report = ExecutionReport(
            results={
                task_id: context.results[task_id].model_copy(deep=True)
                for task_id in list(tasks) + list(compiled.aliases)
            },
            changes=compiled.changes,
            duration_seconds=time.monotonic() - started,
        )
        for output in plan.requested_outputs:
            try:
                report.outputs[output.name] = resolve_reference(output.reference, context.results)
            except ValueError as error:
                report.output_errors[output.name] = str(error)
        return report
