"""Run-scoped context and accounting, with local usage for each invocation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from uuid import uuid4

from pydantic import JsonValue

from ..compiler.schemas import TaskResult, Usage
from ..core.config import Settings
from ..core.tracing import ExecutionEvent, TraceRecorder


@dataclass
class ExecutionContext:
    settings: Settings = field(default_factory=Settings)
    run_id: str = field(default_factory=lambda: uuid4().hex)
    metadata: dict[str, JsonValue] = field(default_factory=dict)
    trace: TraceRecorder = field(default_factory=TraceRecorder)
    results: dict[str, TaskResult] = field(default_factory=dict)
    used_task_ids: set[str] = field(default_factory=set)
    usage: Usage = field(default_factory=Usage)
    started_at: float = field(default_factory=time.monotonic)
    total_tasks: int = 0
    agent_executions: int = 0

    def remaining_seconds(self) -> float:
        return max(0.0, self.settings.run_timeout_seconds - (time.monotonic() - self.started_at))

    def emit(self, kind: str, task_id: str | None = None, **data: JsonValue) -> None:
        self.trace.emit(ExecutionEvent(run_id=self.run_id, kind=kind, task_id=task_id, data=data))

    def reserve_llm_call(self) -> None:
        if self.usage.llm_calls >= self.settings.max_llm_calls:
            raise RuntimeError("Run LLM call limit reached.")
        self.usage.llm_calls += 1


@dataclass(frozen=True)
class AgentContext:
    run: ExecutionContext
    task_id: str
    usage: Usage = field(default_factory=Usage)

    def emit(self, kind: str, **data: JsonValue) -> None:
        self.run.emit(kind, self.task_id, **data)
