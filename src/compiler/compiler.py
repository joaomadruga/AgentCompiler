"""Public compilation and execution API for explicit task DAGs."""

from __future__ import annotations

import asyncio

from ..agents.context import ExecutionContext
from ..agents.registry import AgentRegistry
from ..core.config import Settings
from .optimizations.dead_tasks import eliminate_dead_tasks
from .optimizations.deduplication import deduplicate
from .scheduler import Scheduler
from .schemas import CompiledPlan, ExecutionPlan, ExecutionReport
from .validation import validate_plan


class AgentCompiler:
    def __init__(self, registry: AgentRegistry, settings: Settings | None = None) -> None:
        self.registry = registry.snapshot()
        self.settings = settings or Settings()

    def compile(self, plan: ExecutionPlan, context: ExecutionContext | None = None) -> CompiledPlan:
        context = context or ExecutionContext(settings=self.settings)
        validate_plan(
            plan,
            self.registry,
            context.results,
            used_ids=context.used_task_ids,
            max_tasks=context.settings.max_tasks - context.total_tasks,
        )
        compiled = CompiledPlan(plan=plan.model_copy(deep=True))
        if context.settings.optimize:
            compiled = deduplicate(compiled, self.registry)
            compiled = eliminate_dead_tasks(compiled, self.registry)
        validate_plan(
            compiled.plan,
            self.registry,
            context.results,
            used_ids=context.used_task_ids,
            max_tasks=context.settings.max_tasks - context.total_tasks,
        )
        context.emit(
            "plan_compiled",
            original_tasks=len(plan.tasks),
            executable_tasks=len(compiled.plan.tasks),
            changes=len(compiled.changes),
        )
        for change in compiled.changes:
            context.emit(
                "optimization_applied", change.task_id, **change.model_dump(exclude={"task_id"})
            )
        return compiled

    async def execute(
        self, plan: ExecutionPlan, *, context: ExecutionContext | None = None
    ) -> ExecutionReport:
        context = context or ExecutionContext(settings=self.settings)
        compiled = self.compile(plan, context)
        context.used_task_ids.update(task.id for task in plan.tasks)
        context.total_tasks += len(plan.tasks)
        async with asyncio.timeout(context.remaining_seconds()):
            report = await Scheduler(self.registry).run(compiled, context)
            if context.remaining_seconds() <= 0:
                raise TimeoutError("Run deadline exceeded.")
            return report
