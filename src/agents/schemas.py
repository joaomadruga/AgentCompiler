"""Trusted capability declarations supplied by the application, never by the planner."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field, JsonValue, TypeAdapter, model_validator

from ..compiler.schemas import Contract, Identifier
from ..compiler.type_system import branches, check_model_contract


class Effect(StrEnum):
    PURE = "pure"
    READ = "read"
    WRITE = "write"


class AgentSpec(Contract):
    id: Identifier
    description: str = Field(min_length=1)
    input_schema: dict[str, JsonValue] = Field(
        default_factory=lambda: {"type": "object", "additionalProperties": False}
    )
    output_schema: dict[str, JsonValue] = Field(default_factory=dict)
    input_model: type[BaseModel] | None = Field(default=None, exclude=True)
    output_model: Any = Field(default=None, exclude=True)
    effect: Effect = Effect.WRITE
    reusable: bool = False
    retry_safe: bool = False
    concurrent: bool = True
    estimated_duration_seconds: float = Field(default=1.0, gt=0)
    version: str = "1"

    @model_validator(mode="after")
    def validate_schemas(self) -> AgentSpec:
        if self.input_model is not None:
            if self.input_model.__pydantic_root_model__:
                raise ValueError("Agent input_model must be an object model, not RootModel.")
            check_model_contract(self.input_model)
            object.__setattr__(
                self, "input_schema", self.input_model.model_json_schema(mode="validation")
            )
        if self.output_model is not None:
            if not all(
                isinstance(item, type) and issubclass(item, BaseModel)
                for item in branches(self.output_model)
            ):
                raise ValueError("Agent output_model must be a Pydantic model or model union.")
            check_model_contract(self.output_model)
            object.__setattr__(
                self,
                "output_schema",
                TypeAdapter(self.output_model).json_schema(mode="serialization"),
            )
        Draft202012Validator.check_schema(self.input_schema)
        Draft202012Validator.check_schema(self.output_schema)
        if self.input_schema.get("type") != "object":
            raise ValueError("Agent input_schema must describe an object.")

        def check_references(value: object) -> None:
            if isinstance(value, dict):
                reference = value.get("$ref")
                if reference is not None and not str(reference).startswith("#"):
                    raise ValueError("Agent schemas must use local JSON Schema references.")
                for child in value.values():
                    check_references(child)
            elif isinstance(value, list):
                for child in value:
                    check_references(child)

        check_references(self.input_schema)
        check_references(self.output_schema)
        if self.reusable and self.effect == Effect.WRITE:
            raise ValueError("Write agents cannot declare reusable results.")
        return self
