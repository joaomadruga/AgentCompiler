"""Backward reachability from requested outputs and effectful roots."""

from ...agents.registry import AgentRegistry
from ...agents.schemas import Effect
from ..schemas import CompiledPlan, OptimizationChange


def eliminate_dead_tasks(compiled: CompiledPlan, registry: AgentRegistry) -> CompiledPlan:
    result = compiled.model_copy(deep=True)
    tasks = {task.id: task for task in result.plan.tasks}
    live: set[str] = set()
    stack = [output.reference.task_id for output in result.plan.requested_outputs]
    # Reads may have observable effects; only explicitly pure work is removable.
    stack.extend(
        task.id for task in tasks.values() if registry.spec(task.agent_id).effect != Effect.PURE
    )
    while stack:
        task_id = stack.pop()
        if task_id in tasks and task_id not in live:
            live.add(task_id)
            stack.extend(tasks[task_id].dependency_ids())
    for task in result.plan.tasks:
        if task.id not in live:
            result.changes.append(
                OptimizationChange(
                    pass_name="dead_tasks",
                    task_id=task.id,
                    reason="Pure task does not contribute to a requested output or effectful task.",
                )
            )
    result.plan.tasks = [task for task in result.plan.tasks if task.id in live]
    result.aliases = {alias: target for alias, target in result.aliases.items() if target in live}
    return result
