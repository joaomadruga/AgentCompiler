"""Run a small task DAG with real Python operations and no LLM credentials.

This is a usage example, not a benchmark or unit test.
Run: uv run python -m examples.parallel_plan
"""

from __future__ import annotations

import asyncio
import json

from src import (
    AgentCompiler,
    AgentContext,
    AgentRegistry,
    AgentSpec,
    Effect,
    ExecutionPlan,
    FunctionAgent,
    InputBinding,
    OutputReference,
    RequestedOutput,
    Settings,
    Task,
)


async def describe_text(instruction: str, inputs: dict, context: AgentContext) -> dict:
    await asyncio.sleep(0)  # Yield to other runnable tasks.
    text = inputs["text"]
    return {"words": len(text.split()), "characters": len(text)}


async def combine(instruction: str, inputs: dict, context: AgentContext) -> dict:
    return {"total_words": inputs["left"]["words"] + inputs["right"]["words"]}


def build_registry() -> AgentRegistry:
    return AgentRegistry(
        [
            FunctionAgent(
                AgentSpec(
                    id="describe",
                    description="Count words and characters in supplied text.",
                    input_schema={
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                        "additionalProperties": False,
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "words": {"type": "integer"},
                            "characters": {"type": "integer"},
                        },
                        "required": ["words", "characters"],
                        "additionalProperties": False,
                    },
                    effect=Effect.PURE,
                    reusable=True,
                    retry_safe=True,
                ),
                describe_text,
            ),
            FunctionAgent(
                AgentSpec(
                    id="combine",
                    description="Sum word counts from two descriptions.",
                    input_schema={
                        "type": "object",
                        "properties": {"left": {"type": "object"}, "right": {"type": "object"}},
                        "required": ["left", "right"],
                        "additionalProperties": False,
                    },
                    output_schema={
                        "type": "object",
                        "properties": {"total_words": {"type": "integer"}},
                        "required": ["total_words"],
                        "additionalProperties": False,
                    },
                    effect=Effect.PURE,
                    reusable=True,
                    retry_safe=True,
                ),
                combine,
            ),
        ]
    )


def build_plan() -> ExecutionPlan:
    return ExecutionPlan(
        tasks=[
            Task(
                id="left",
                agent_id="describe",
                instruction="Count the supplied text.",
                inputs=[InputBinding(name="text", value="Dependencies enable parallel execution")],
            ),
            Task(
                id="right",
                agent_id="describe",
                instruction="Count the supplied text.",
                inputs=[InputBinding(name="text", value="A compiler can eliminate redundant work")],
            ),
            Task(
                id="duplicate",
                agent_id="describe",
                instruction="Count the supplied text.",
                inputs=[InputBinding(name="text", value="Dependencies enable parallel execution")],
            ),
            Task(
                id="unused",
                agent_id="describe",
                instruction="Count the supplied text.",
                inputs=[InputBinding(name="text", value="This pure output is not requested")],
            ),
            Task(
                id="combined",
                agent_id="combine",
                instruction="Sum both word counts.",
                inputs=[
                    InputBinding(name="left", reference=OutputReference(task_id="duplicate")),
                    InputBinding(name="right", reference=OutputReference(task_id="right")),
                ],
            ),
        ],
        requested_outputs=[
            RequestedOutput(name="summary", reference=OutputReference(task_id="combined"))
        ],
    )


async def main() -> None:
    report = await AgentCompiler(build_registry(), Settings()).execute(build_plan())
    print(json.dumps(report.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
