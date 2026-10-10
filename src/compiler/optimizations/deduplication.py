"""Common subexpression elimination for explicitly reusable task contracts."""

from __future__ import annotations

import json

from ...agents.registry import AgentRegistry
from ...agents.schemas import Effect
from ..schemas import CompiledPlan, OptimizationChange
from ..validation import topological_order


def deduplicate(compiled: CompiledPlan, registry: AgentRegistry) -> CompiledPlan:
    result = compiled.model_copy(deep=True)
    tasks = {task.id: task for task in result.plan.tasks}
    signatures: dict[str, str] = {}
    kept = []
    for task_id in topological_order(result.plan):
        task = tasks[task_id]
        task.dependencies = sorted({result.aliases.get(dep, dep) for dep in task.dependencies})
        for binding in task.inputs:
            if binding.reference:
                binding.reference.task_id = result.aliases.get(
                    binding.reference.task_id, binding.reference.task_id
                )
        spec = registry.spec(task.agent_id)
        signature = json.dumps(
            {
                "agent": spec.id,
                "version": spec.version,
                "instruction": task.instruction,
                "inputs": sorted(
                    [binding.model_dump(mode="json") for binding in task.inputs],
                    key=lambda binding: binding["name"],
                ),
                "dependencies": sorted(task.dependency_ids()),
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        if spec.reusable and spec.effect != Effect.WRITE and signature in signatures:
            replacement = signatures[signature]
            result.aliases[task.id] = replacement
            result.changes.append(
                OptimizationChange(
                    pass_name="deduplication",
                    task_id=task.id,
                    replacement_id=replacement,
                    reason="Identical inputs and instruction under a reusable agent contract.",
                )
            )
        else:
            kept.append(task)
            if spec.reusable and spec.effect != Effect.WRITE:
                signatures[signature] = task.id
    result.plan.tasks = kept
    for output in result.plan.requested_outputs:
        output.reference.task_id = result.aliases.get(
            output.reference.task_id, output.reference.task_id
        )
    return result
