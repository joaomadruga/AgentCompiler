"""Serializable intermediate representation and execution reports."""

from __future__ import annotations

import json
import re
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$", max_length=128)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, allow_inf_nan=False)


class OutputReference(Contract):
    task_id: Identifier
    path: str = Field(
        default="", description="RFC 6901 JSON pointer; empty selects the entire output."
    )

    @model_validator(mode="after")
    def check_path(self) -> OutputReference:
        if self.path and not self.path.startswith("/"):
            raise ValueError("Reference paths must be empty or start with '/'.")
        if re.search(r"~(?![01])", self.path):
            raise ValueError("Invalid JSON pointer escape.")
        return self


class InputBinding(Contract):
    name: Identifier
    value: JsonValue = None
    reference: OutputReference | None = None

    @model_validator(mode="after")
    def check_source(self) -> InputBinding:
        json.dumps(self.value, allow_nan=False)
        if self.reference is not None and self.value is not None:
            raise ValueError("A binding cannot contain both a literal and a reference.")
        return self


class RequestedOutput(Contract):
    name: Identifier
    reference: OutputReference


class Task(Contract):
    id: Identifier
    agent_id: Identifier
    instruction: str = Field(min_length=1, max_length=16000)
    inputs: list[InputBinding] = Field(default_factory=list)
    dependencies: list[Identifier] = Field(default_factory=list)

    def dependency_ids(self) -> set[str]:
        return set(self.dependencies) | {
            binding.reference.task_id for binding in self.inputs if binding.reference is not None
        }


class ExecutionPlan(Contract):
    tasks: list[Task] = Field(default_factory=list)
    requested_outputs: list[RequestedOutput] = Field(default_factory=list)


class TaskStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class Usage(Contract):
    llm_calls: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0

    def add(self, other: Usage) -> None:
        for name in type(self).model_fields:
            setattr(self, name, getattr(self, name) + getattr(other, name))


class TaskResult(Contract):
    task_id: str
    agent_id: str
    status: TaskStatus
    output: JsonValue = None
    error: str | None = None
    attempts: int = 0
    duration_seconds: float = 0.0
    reused_from: str | None = None
    usage: Usage = Field(default_factory=Usage)


class OptimizationChange(Contract):
    pass_name: str
    task_id: str
    replacement_id: str | None = None
    reason: str


class CompiledPlan(Contract):
    plan: ExecutionPlan
    aliases: dict[str, str] = Field(default_factory=dict)
    changes: list[OptimizationChange] = Field(default_factory=list)


class ExecutionReport(Contract):
    results: dict[str, TaskResult] = Field(default_factory=dict)
    outputs: dict[str, JsonValue] = Field(default_factory=dict)
    output_errors: dict[str, str] = Field(default_factory=dict)
    changes: list[OptimizationChange] = Field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def successful(self) -> bool:
        return not self.output_errors and all(
            result.status == TaskStatus.SUCCEEDED for result in self.results.values()
        )
