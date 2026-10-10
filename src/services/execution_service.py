"""Bounded plan/compile/execute/synthesize lifecycle with preserved prior results."""

from __future__ import annotations

import asyncio
import time
from copy import deepcopy

from pydantic import JsonValue, TypeAdapter

from ..agents.context import ExecutionContext
from ..agents.orchestrator.agent import Orchestrator, OrchestratorAgent
from ..agents.orchestrator.schemas import RunResult
from ..agents.registry import AgentRegistry
from ..compiler.compiler import AgentCompiler
from ..core.config import Settings
from ..core.llm import LanguageModel
from ..core.tracing import TraceRecorder


class ExecutionService:
    def __init__(
        self, registry: AgentRegistry, orchestrator: Orchestrator, settings: Settings | None = None
    ) -> None:
        self.settings = settings or Settings()
        self.compiler = AgentCompiler(registry, self.settings)
        self.orchestrator = orchestrator

    @classmethod
    def from_model(
        cls, registry: AgentRegistry, model: LanguageModel, settings: Settings | None = None
    ) -> ExecutionService:
        return cls(registry, OrchestratorAgent(registry, model), settings)

    async def run(
        self,
        request: str,
        *,
        metadata: dict[str, JsonValue] | None = None,
        trace: TraceRecorder | None = None,
    ) -> RunResult:
        if not request.strip():
            raise ValueError("Request must not be empty.")
        context = ExecutionContext(
            settings=self.settings.model_copy(deep=True),
            metadata=TypeAdapter(dict[str, JsonValue]).validate_python(deepcopy(metadata or {})),
            trace=trace if trace is not None else TraceRecorder(),
        )
        context.emit("run_started")
        rounds = []
        status = "failed"
        answer = None
        error_message = None
        feedback = ""
        try:
            async with asyncio.timeout(context.settings.run_timeout_seconds):
                for index in range(context.settings.max_rounds):
                    context.emit("round_started", round=index + 1)
                    plan = await self.orchestrator.generate_plan(
                        request, context, feedback=feedback
                    )
                    report = await self.compiler.execute(plan, context=context)
                    rounds.append(report)
                    allow_replan = (
                        index + 1 < context.settings.max_rounds
                        and context.total_tasks < context.settings.max_tasks
                    )
                    decision = await self.orchestrator.synthesize(
                        request, report, context, allow_replan=allow_replan
                    )
                    if decision.action == "replan":
                        if not allow_replan:
                            status = "stopped"
                            error_message = (
                                "Replanning requested after the run budget was exhausted."
                            )
                            break
                        feedback = decision.feedback
                        continue
                    answer = decision.final_answer
                    status = "completed" if decision.action == "answer" else "stopped"
                    break
        except TimeoutError:
            status = "timed_out"
            error_message = "Run deadline exceeded; inspect results for partial work."
        except asyncio.CancelledError:
            context.emit("run_cancelled")
            raise
        except Exception as error:
            status = "timed_out" if context.remaining_seconds() <= 0 else "failed"
            error_message = f"{type(error).__name__}: {error}"
        context.emit("run_finished", status=status)
        return RunResult(
            run_id=context.run_id,
            status=status,
            final_answer=answer,
            error=error_message,
            rounds=rounds,
            results={key: value.model_copy(deep=True) for key, value in context.results.items()},
            usage=context.usage.model_copy(deep=True),
            agent_executions=context.agent_executions,
            duration_seconds=time.monotonic() - context.started_at,
            events=[
                event.model_copy(deep=True)
                for event in context.trace.events
                if event.run_id == context.run_id
            ],
        )
