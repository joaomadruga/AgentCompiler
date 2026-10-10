"""Callable and LLM-backed specialists with typed contracts and real tool invocation."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, JsonValue, TypeAdapter

from .context import AgentContext
from .schemas import AgentSpec, Effect

if TYPE_CHECKING:
    from ..core.llm import LanguageModel

JSON = TypeAdapter(JsonValue)
AgentHandler = Callable[[str, dict[str, JsonValue], AgentContext], Awaitable[JsonValue | BaseModel]]


def serialize_output(value: JsonValue | BaseModel) -> JsonValue:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return JSON.validate_python(value)


class AgentExecutionError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class Agent(Protocol):
    spec: AgentSpec

    async def run(
        self, instruction: str, inputs: dict[str, JsonValue], context: AgentContext
    ) -> JsonValue: ...


class FunctionAgent:
    """Wrap an async function; blocking integrations must provide their own async adapter."""

    def __init__(self, spec: AgentSpec, handler: AgentHandler) -> None:
        if not inspect.iscoroutinefunction(handler):
            raise TypeError("FunctionAgent requires an async handler.")
        self.spec = spec.model_copy(deep=True)
        self.handler = handler
        self._lock = asyncio.Lock()

    async def run(
        self, instruction: str, inputs: dict[str, JsonValue], context: AgentContext
    ) -> JsonValue:
        if not self.spec.concurrent:
            async with self._lock:
                return serialize_output(await self.handler(instruction, inputs, context))
        return serialize_output(await self.handler(instruction, inputs, context))


class LLMAgent:
    """Execute a caller-provided role prompt with optional registered tools."""

    def __init__(
        self,
        spec: AgentSpec,
        model: LanguageModel,
        system_prompt: str,
        *,
        tools: list[Agent] | None = None,
    ) -> None:
        if not system_prompt.strip():
            raise ValueError("system_prompt must not be empty.")
        self.spec = spec.model_copy(deep=True)
        self.model = model
        self.system_prompt = system_prompt
        self._lock = asyncio.Lock()
        self.tools = tuple(tools or ())
        if any(len(tool.spec.id) > 64 for tool in self.tools):
            raise ValueError("LLM tool IDs must contain at most 64 characters.")
        if len({tool.spec.id for tool in self.tools}) != len(self.tools):
            raise ValueError("Tool IDs must be unique.")
        if self.spec.effect == Effect.PURE and any(
            tool.spec.effect != Effect.PURE for tool in self.tools
        ):
            raise ValueError("Pure agents require pure tools.")
        if any(tool.spec.effect == Effect.WRITE for tool in self.tools):
            if self.spec.effect != Effect.WRITE:
                raise ValueError("An agent with write tools must declare write effects.")
        if self.spec.reusable and any(not tool.spec.reusable for tool in self.tools):
            raise ValueError("Reusable agents require reusable tools.")
        if self.spec.retry_safe and any(not tool.spec.retry_safe for tool in self.tools):
            raise ValueError("Retry-safe agents require retry-safe tools.")
        if self.spec.concurrent and any(not tool.spec.concurrent for tool in self.tools):
            raise ValueError("Concurrent agents require concurrent tools.")

    async def run(
        self, instruction: str, inputs: dict[str, JsonValue], context: AgentContext
    ) -> JsonValue:
        if not self.spec.concurrent:
            async with self._lock:
                return await self._run(instruction, inputs, context)
        return await self._run(instruction, inputs, context)

    async def _run(
        self, instruction: str, inputs: dict[str, JsonValue], context: AgentContext
    ) -> JsonValue:
        return await self.model.run_agent(
            system_prompt=self.system_prompt,
            instruction=instruction,
            inputs=inputs,
            output_schema=self.spec.output_schema,
            tools=list(self.tools),
            context=context,
        )
