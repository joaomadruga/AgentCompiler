"""LLM planning and evidence-grounded synthesis over a trusted agent catalog."""

from __future__ import annotations

from typing import Protocol

from ...compiler.schemas import ExecutionPlan, ExecutionReport, TaskStatus
from ...compiler.validation import validate_plan
from ...core.llm import LanguageModel
from ..context import ExecutionContext
from ..registry import AgentRegistry
from .prompts.planning import PLANNING_PROMPT
from .prompts.synthesis import SYNTHESIS_PROMPT
from .schemas import SynthesisDecision


class Orchestrator(Protocol):
    async def generate_plan(
        self, request: str, context: ExecutionContext, *, feedback: str = ""
    ) -> ExecutionPlan: ...

    async def synthesize(
        self,
        request: str,
        report: ExecutionReport,
        context: ExecutionContext,
        *,
        allow_replan: bool,
    ) -> SynthesisDecision: ...


class OrchestratorAgent:
    def __init__(self, registry: AgentRegistry, model: LanguageModel) -> None:
        self.registry = registry.snapshot()
        self.model = model

    async def generate_plan(
        self, request: str, context: ExecutionContext, *, feedback: str = ""
    ) -> ExecutionPlan:
        context.emit("planning_started")
        payload = {
            "request": request,
            "agents": self.registry.catalog(),
            "feedback": feedback,
            "used_task_ids": sorted(context.used_task_ids),
            "remaining_tasks": context.settings.max_tasks - context.total_tasks,
            "previous_results": {
                key: result.model_dump(mode="json") for key, result in context.results.items()
            },
        }
        plan = await self.model.structured(
            PLANNING_PROMPT,
            payload,
            ExecutionPlan,
            context,
            validator=lambda plan: validate_plan(
                plan,
                self.registry,
                context.results,
                used_ids=context.used_task_ids,
                max_tasks=context.settings.max_tasks - context.total_tasks,
            ),
        )
        context.emit("planning_finished", tasks=len(plan.tasks))
        return plan

    async def synthesize(
        self,
        request: str,
        report: ExecutionReport,
        context: ExecutionContext,
        *,
        allow_replan: bool,
    ) -> SynthesisDecision:
        context.emit("synthesis_started")
        decision = await self.model.structured(
            SYNTHESIS_PROMPT,
            {
                "request": request,
                "agents": self.registry.catalog(),
                "allow_replan": allow_replan,
                "remaining_tasks": context.settings.max_tasks - context.total_tasks,
                "outputs": report.outputs,
                "output_errors": report.output_errors,
                "results": {
                    key: result.model_dump(mode="json") for key, result in context.results.items()
                },
                "successful_task_ids": [
                    key
                    for key, result in context.results.items()
                    if result.status == TaskStatus.SUCCEEDED
                ],
            },
            SynthesisDecision,
            context,
        )
        context.emit("synthesis_finished", action=decision.action)
        return decision
