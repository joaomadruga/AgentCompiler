"""Snapshot-friendly registration of trusted agent executables and capabilities."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from ..compiler.type_system import contract_catalog
from .base import Agent
from .schemas import AgentSpec


class AgentRegistry:
    def __init__(self, agents: Iterable[Agent] = ()) -> None:
        self._agents: dict[str, Agent] = {}
        self._specs: dict[str, AgentSpec] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        for agent in agents:
            self.register(agent)

    def register(self, agent: Agent) -> None:
        spec = AgentSpec.model_validate(
            {
                **agent.spec.model_dump(),
                "input_model": agent.spec.input_model,
                "output_model": agent.spec.output_model,
            }
        )
        if spec.id in self._agents:
            raise ValueError(f"Agent already registered: {spec.id}")
        self._agents[spec.id] = agent
        self._specs[spec.id] = spec
        self._locks[spec.id] = asyncio.Lock()

    def get(self, agent_id: str) -> Agent:
        try:
            return self._agents[agent_id]
        except KeyError as error:
            raise ValueError(f"Unknown agent: {agent_id}") from error

    def spec(self, agent_id: str) -> AgentSpec:
        self.get(agent_id)
        return self._specs[agent_id].model_copy(deep=True)

    def lock(self, agent_id: str) -> asyncio.Lock:
        self.get(agent_id)
        return self._locks[agent_id]

    def catalog(self) -> list[dict]:
        catalog = []
        for spec in self._specs.values():
            entry = spec.model_dump(mode="json")
            if spec.input_model is not None:
                entry["input_contract"] = contract_catalog(spec.input_model)
            if spec.output_model is not None:
                entry["output_contract"] = contract_catalog(spec.output_model)
            catalog.append(entry)
        return catalog

    def snapshot(self) -> AgentRegistry:
        snapshot = AgentRegistry()
        snapshot._agents = self._agents.copy()
        snapshot._locks = self._locks.copy()
        snapshot._specs = {key: spec.model_copy(deep=True) for key, spec in self._specs.items()}
        return snapshot
