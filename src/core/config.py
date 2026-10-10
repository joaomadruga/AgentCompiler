"""Validated runtime settings loaded from environment variables or explicit arguments."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENTCOMPILER_", env_file=".env", extra="ignore", allow_inf_nan=False
    )

    max_concurrency: int = Field(default=4, ge=1, le=256)
    max_tasks: int = Field(default=128, ge=1)
    max_rounds: int = Field(default=3, ge=1)
    max_plan_attempts: int = Field(default=3, ge=1)
    max_task_attempts: int = Field(default=2, ge=1)
    max_tool_calls: int = Field(default=12, ge=0)
    max_llm_calls: int = Field(default=100, ge=1)
    run_timeout_seconds: float = Field(default=300.0, gt=0)
    task_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    retry_backoff_seconds: float = Field(default=0.5, ge=0)
    optimize: bool = True
    scheduling: Literal["fifo", "critical_path"] = "fifo"
    llm_model: str = "gpt-4o-mini"
    specialist_model: str | None = None
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_max_tokens: int = Field(default=4096, ge=1)
    llm_temperature: float | None = None
    structured_mode: Literal["json_object", "json_schema"] = "json_object"
    input_cost_per_million: float = Field(default=0.0, ge=0)
    output_cost_per_million: float = Field(default=0.0, ge=0)
