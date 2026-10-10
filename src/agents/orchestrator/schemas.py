"""Structured decisions and final run reports."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ...compiler.schemas import Contract, ExecutionReport, TaskResult, Usage
from ...core.tracing import ExecutionEvent


class SynthesisDecision(Contract):
    action: Literal["answer", "replan", "stop"]
    final_answer: str | None = None
    feedback: str = ""

    @model_validator(mode="after")
    def check_decision(self) -> SynthesisDecision:
        if self.action in {"answer", "stop"} and not (self.final_answer or "").strip():
            raise ValueError("Answer and stop decisions require a nonempty final_answer.")
        if self.action == "replan" and not self.feedback.strip():
            raise ValueError("Replanning requires actionable feedback.")
        return self


class RunResult(Contract):
    run_id: str
    status: Literal["completed", "stopped", "failed", "timed_out"]
    final_answer: str | None = None
    error: str | None = None
    rounds: list[ExecutionReport] = Field(default_factory=list)
    results: dict[str, TaskResult] = Field(default_factory=dict)
    usage: Usage = Field(default_factory=Usage)
    agent_executions: int = 0
    duration_seconds: float = 0.0
    events: list[ExecutionEvent] = Field(default_factory=list)
