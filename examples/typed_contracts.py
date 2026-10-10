"""Demonstrate typed rejection, correction and execution without LLM credentials.

This is a local usage example, not a benchmark, payment integration or unit test.
Run: uv run python -m examples.typed_contracts
"""

from __future__ import annotations

import asyncio
import json

from pydantic import BaseModel, ConfigDict, Field

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
    PlanValidationError,
    RequestedOutput,
    Task,
)


class Data(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Purchase(Data):
    purchase_id: str


class ConfirmedPayment(Purchase):
    transaction_id: str


class RefundAuthorization(Data):
    purchase_id: str
    amount_cents: int = Field(gt=0)


class RefundReceipt(Data):
    purchase_id: str
    amount_cents: int
    receipt_id: str


class VerifyInput(Data):
    purchase_id: str


class AuthorizeInput(Data):
    payment: ConfirmedPayment


class RefundInput(Data):
    authorization: RefundAuthorization


async def verify(instruction: str, inputs: dict, context: AgentContext) -> ConfirmedPayment:
    return ConfirmedPayment(purchase_id=inputs["purchase_id"], transaction_id="local-payment")


async def authorize(instruction: str, inputs: dict, context: AgentContext) -> RefundAuthorization:
    return RefundAuthorization(purchase_id=inputs["payment"]["purchase_id"], amount_cents=1200)


async def refund(instruction: str, inputs: dict, context: AgentContext) -> RefundReceipt:
    return RefundReceipt(**inputs["authorization"], receipt_id="local-receipt")


def build_registry() -> AgentRegistry:
    return AgentRegistry(
        [
            FunctionAgent(
                AgentSpec(
                    id="verify",
                    description="Produce local illustrative payment data.",
                    input_model=VerifyInput,
                    output_model=ConfirmedPayment,
                    effect=Effect.PURE,
                ),
                verify,
            ),
            FunctionAgent(
                AgentSpec(
                    id="authorize",
                    description="Produce local illustrative refund data.",
                    input_model=AuthorizeInput,
                    output_model=RefundAuthorization,
                    effect=Effect.PURE,
                ),
                authorize,
            ),
            FunctionAgent(
                AgentSpec(
                    id="refund",
                    description="Produce a local receipt without any external effect.",
                    input_model=RefundInput,
                    output_model=RefundReceipt,
                    effect=Effect.PURE,
                ),
                refund,
            ),
        ]
    )


def build_plan(*, corrected: bool) -> ExecutionPlan:
    tasks = [
        Task(
            id="payment",
            agent_id="verify",
            instruction="Produce local payment data.",
            inputs=[InputBinding(name="purchase_id", value="purchase-123")],
        )
    ]
    if corrected:
        tasks.append(
            Task(
                id="authorization",
                agent_id="authorize",
                instruction="Produce local authorization data.",
                inputs=[InputBinding(name="payment", reference=OutputReference(task_id="payment"))],
            )
        )
    tasks.append(
        Task(
            id="receipt",
            agent_id="refund",
            instruction="Produce a local receipt.",
            inputs=[
                InputBinding(
                    name="authorization",
                    reference=OutputReference(task_id="authorization" if corrected else "payment"),
                )
            ],
        )
    )
    return ExecutionPlan(
        tasks=tasks,
        requested_outputs=[
            RequestedOutput(
                name="receipt",
                reference=OutputReference(task_id="receipt"),
            )
        ],
    )


async def main() -> None:
    compiler = AgentCompiler(build_registry())
    try:
        compiler.compile(build_plan(corrected=False))
    except PlanValidationError as error:
        print("Rejected before execution:")
        print(json.dumps(error.as_dict(), indent=2))
    # This example supplies the correction explicitly; a live orchestrator would propose it.
    report = await compiler.execute(build_plan(corrected=True))
    print("Corrected plan outputs:")
    print(json.dumps(report.outputs, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
