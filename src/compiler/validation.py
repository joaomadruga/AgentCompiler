"""Graph validation and RFC 6901 reference resolution."""

from __future__ import annotations

import json
from collections import deque
from copy import deepcopy
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import BaseModel, JsonValue

from ..agents.registry import AgentRegistry
from .schemas import ExecutionPlan, OutputReference, PlanDiagnostic, Task, TaskResult, TaskStatus
from .type_system import (
    assignable,
    type_at_pointer,
    type_name,
    validate_input_model,
    validate_json_type,
)


class PlanValidationError(ValueError):
    def __init__(self, issues: list[str], diagnostics: list[PlanDiagnostic] | None = None) -> None:
        self.issues = issues
        self.diagnostics = diagnostics or [
            PlanDiagnostic(code="invalid_plan", message=issue) for issue in issues
        ]
        super().__init__("Invalid execution plan: " + json.dumps(self.as_dict()))

    def as_dict(self) -> dict:
        return {"diagnostics": [item.model_dump(mode="json") for item in self.diagnostics]}


def validate_value(value: JsonValue, schema: dict, label: str) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: str(e.path))
    if errors:
        raise ValueError(f"{label}: " + "; ".join(error.message for error in errors[:10]))


def resolve_reference(reference: OutputReference, results: dict[str, TaskResult]) -> JsonValue:
    result = results.get(reference.task_id)
    if result is None or result.status != TaskStatus.SUCCEEDED:
        raise ValueError(f"Referenced task has no successful result: {reference.task_id}")
    value = result.output
    for token in reference.path.split("/")[1:]:
        key = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not key.isdigit() or (len(key) > 1 and key.startswith("0")):
                raise ValueError(f"Invalid array index in reference: {reference.path}")
            try:
                value = value[int(key)]
            except IndexError as error:
                raise ValueError(f"Missing reference path: {reference.path}") from error
        elif isinstance(value, dict) and key in value:
            value = value[key]
        else:
            raise ValueError(f"Missing reference path: {reference.path}")
    return deepcopy(value)


def resolve_inputs(task: Task, results: dict[str, TaskResult]) -> dict[str, JsonValue]:
    return {
        binding.name: resolve_reference(binding.reference, results)
        if binding.reference
        else deepcopy(binding.value)
        for binding in task.inputs
    }


def topological_order(plan: ExecutionPlan) -> list[str]:
    tasks = {task.id: task for task in plan.tasks}
    incoming = {task.id: len(task.dependency_ids() & tasks.keys()) for task in plan.tasks}
    children: dict[str, list[str]] = {task.id: [] for task in plan.tasks}
    for task in plan.tasks:
        for dependency in task.dependency_ids() & tasks.keys():
            children[dependency].append(task.id)
    ready = deque(task.id for task in plan.tasks if incoming[task.id] == 0)
    order: list[str] = []
    while ready:
        task_id = ready.popleft()
        order.append(task_id)
        for child in children[task_id]:
            incoming[child] -= 1
            if incoming[child] == 0:
                ready.append(child)
    if len(order) != len(tasks):
        raise PlanValidationError(["Dependency graph contains a cycle."])
    return order


def validate_plan(
    plan: ExecutionPlan,
    registry: AgentRegistry,
    previous: dict[str, TaskResult] | None = None,
    *,
    used_ids: set[str] | None = None,
    max_tasks: int = 128,
) -> None:
    previous = previous or {}
    issues: list[str] = []
    diagnostics: list[PlanDiagnostic] = []
    tasks = {task.id: task for task in plan.tasks}
    if len(tasks) != len(plan.tasks):
        issues.append("Task IDs must be unique.")
    if len(plan.tasks) > max_tasks:
        issues.append(f"Task budget exceeded: at most {max_tasks} new tasks allowed.")
    collisions = tasks.keys() & (set(previous) | (used_ids or set()))
    if collisions:
        issues.append(f"New task IDs must not reuse previous IDs: {sorted(collisions)}")
    output_names = [output.name for output in plan.requested_outputs]
    if len(set(output_names)) != len(output_names):
        issues.append("Requested output names must be unique.")
    if plan.tasks and not plan.requested_outputs:
        issues.append("A nonempty plan must declare its requested outputs.")

    def check_reference(reference: OutputReference) -> None:
        if reference.task_id in tasks:
            try:
                source = registry.spec(tasks[reference.task_id].agent_id)
                schema_at_pointer(source.output_schema, reference.path)
            except (ValueError, KeyError) as error:
                issues.append(str(error))
        else:
            try:
                resolve_reference(reference, previous)
            except ValueError as error:
                issues.append(str(error))

    for task in plan.tasks:
        names = [binding.name for binding in task.inputs]
        if len(names) != len(set(names)):
            issues.append(f"Task {task.id}: input names must be unique.")
        if len(set(task.dependencies)) != len(task.dependencies):
            issues.append(f"Task {task.id}: dependencies must be unique.")
        for dependency in sorted(task.dependency_ids()):
            if dependency == task.id:
                issues.append(f"Task {task.id}: self-dependency is not allowed.")
            if dependency not in tasks:
                result = previous.get(dependency)
                if result is None or result.status != TaskStatus.SUCCEEDED:
                    issues.append(f"Task {task.id}: unavailable dependency {dependency}.")
        for binding in task.inputs:
            if binding.reference:
                check_reference(binding.reference)
        try:
            spec = registry.spec(task.agent_id)
        except ValueError as error:
            issues.append(str(error))
            continue
        if spec.input_model is not None:
            typed_issues = validate_typed_bindings(
                task, spec.input_model, tasks, registry, previous
            )
            diagnostics.extend(typed_issues)
            issues.extend(item.message for item in typed_issues)
            continue
        required = set(spec.input_schema.get("required", []))
        properties = spec.input_schema.get("properties", {})
        if not required.issubset(names):
            issues.append(
                f"Task {task.id}: missing required inputs {sorted(required - set(names))}."
            )
        if spec.input_schema.get("additionalProperties") is False:
            if extra := set(names) - properties.keys():
                issues.append(f"Task {task.id}: unknown inputs {sorted(extra)}.")
        for binding in task.inputs:
            if binding.reference is not None:
                try:
                    if binding.reference.task_id in tasks:
                        source_spec = registry.spec(tasks[binding.reference.task_id].agent_id)
                        source_schema = schema_at_pointer(
                            source_spec.output_schema, binding.reference.path
                        )
                        target_schema = schema_at_pointer(spec.input_schema, "/" + binding.name)
                        if not compatible_types(source_schema, target_schema):
                            issues.append(
                                f"Task {task.id}: incompatible reference type "
                                f"for input {binding.name}."
                            )
                    else:
                        value = resolve_reference(binding.reference, previous)
                        validator = Draft202012Validator(spec.input_schema).evolve(
                            schema=properties.get(binding.name, {})
                        )
                        errors = list(validator.iter_errors(value))
                        if errors:
                            issues.append(f"Task {task.id}: {errors[0].message}")
                except (ValueError, KeyError) as error:
                    issues.append(str(error))
            else:
                schema = properties.get(binding.name, {})
                try:
                    errors = list(
                        Draft202012Validator(spec.input_schema)
                        .evolve(schema=schema)
                        .iter_errors(binding.value)
                    )
                    if errors:
                        raise ValueError(
                            f"Task {task.id} input {binding.name}: {errors[0].message}"
                        )
                except ValueError as error:
                    issues.append(str(error))
        if all(binding.reference is None for binding in task.inputs):
            try:
                validate_value(
                    resolve_inputs(task, {}), spec.input_schema, f"Task {task.id} inputs"
                )
            except ValueError as error:
                issues.append(str(error))
    for output in plan.requested_outputs:
        check_reference(output.reference)
    if not issues:
        topological_order(plan)
    if issues:
        typed_messages = {item.message for item in diagnostics}
        diagnostics.extend(
            PlanDiagnostic(code="invalid_plan", message=issue)
            for issue in issues
            if issue not in typed_messages
        )
        raise PlanValidationError(issues, diagnostics)


def validate_typed_bindings(
    task: Task,
    model: type[BaseModel],
    tasks: dict[str, Task],
    registry: AgentRegistry,
    previous: dict[str, TaskResult],
) -> list[PlanDiagnostic]:
    diagnostics: list[PlanDiagnostic] = []
    names = {binding.name for binding in task.inputs}
    for name, field in model.model_fields.items():
        if field.is_required() and name not in names:
            diagnostics.append(
                PlanDiagnostic(
                    code="missing_input",
                    message=f"Task {task.id}: missing required input {name}.",
                    task_id=task.id,
                    input_name=name,
                    expected_type=type_name(field.rebuild_annotation()),
                )
            )
    for binding in task.inputs:
        field = model.model_fields.get(binding.name)
        if field is None:
            diagnostics.append(
                PlanDiagnostic(
                    code="unknown_input",
                    message=f"Task {task.id}: unknown input {binding.name}.",
                    task_id=task.id,
                    input_name=binding.name,
                )
            )
            continue
        target = field.rebuild_annotation()
        source = None
        try:
            if binding.reference is None:
                validate_json_type(target, binding.value)
            else:
                ref = binding.reference
                source_id = (
                    tasks[ref.task_id].agent_id
                    if ref.task_id in tasks
                    else (previous[ref.task_id].agent_id)
                )
                producer = registry.spec(source_id)
                if producer.output_model is None:
                    raise ValueError("Typed inputs require a producer with an output_model.")
                source = type_at_pointer(producer.output_model, ref.path)
                if not assignable(source, target):
                    diagnostics.append(
                        PlanDiagnostic(
                            code="incompatible_type",
                            message=f"Task {task.id}: incompatible type for input {binding.name}.",
                            task_id=task.id,
                            input_name=binding.name,
                            source_task_id=ref.task_id,
                            expected_type=type_name(target),
                            received_type=type_name(source),
                        )
                    )
                elif ref.task_id not in tasks:
                    validate_json_type(source, resolve_reference(ref, previous))
        except (ValueError, KeyError, TypeError) as error:
            diagnostics.append(
                PlanDiagnostic(
                    code="invalid_binding",
                    message=f"Task {task.id} input {binding.name}: {error}",
                    task_id=task.id,
                    input_name=binding.name,
                    source_task_id=binding.reference.task_id if binding.reference else None,
                    expected_type=type_name(target),
                    received_type=type_name(source) if source is not None else None,
                )
            )
    if not diagnostics and all(binding.reference is None for binding in task.inputs):
        try:
            validate_input_model(model, resolve_inputs(task, {}), {})
        except ValueError as error:
            diagnostics.append(
                PlanDiagnostic(
                    code="invalid_inputs",
                    message=f"Task {task.id}: {error}",
                    task_id=task.id,
                )
            )
    return diagnostics


def reference_input_types(
    task: Task, registry: AgentRegistry, results: dict[str, TaskResult]
) -> dict[str, Any]:
    sources = {}
    for binding in task.inputs:
        if binding.reference is not None:
            result = results[binding.reference.task_id]
            producer = registry.spec(result.agent_id)
            if producer.output_model is None:
                raise ValueError("Typed inputs require a producer with an output_model.")
            sources[binding.name] = type_at_pointer(producer.output_model, binding.reference.path)
    return sources


def schema_at_pointer(schema: dict, pointer: str) -> dict | None:
    """Resolve known schema paths; return None when a contract leaves the shape open."""
    root = schema
    current = schema
    for token in [None] + pointer.split("/")[1:]:
        seen = set()
        while "$ref" in current:
            reference = current["$ref"]
            if reference in seen:
                return None
            seen.add(reference)
            if not reference.startswith("#/"):
                return None
            current = root
            for part in reference[2:].split("/"):
                current = current[part.replace("~1", "/").replace("~0", "~")]
        if token is None:
            continue
        key = token.replace("~1", "/").replace("~0", "~")
        if "anyOf" in current or "oneOf" in current or "allOf" in current:
            return None
        properties = current.get("properties", {})
        if key in properties:
            current = properties[key]
        elif current.get("type") == "array":
            if not key.isdigit() or (len(key) > 1 and key.startswith("0")):
                raise ValueError(f"Invalid array reference path: {pointer}")
            prefix = current.get("prefixItems", [])
            if int(key) < len(prefix):
                current = prefix[int(key)]
            elif isinstance(current.get("items"), dict):
                current = current["items"]
            elif current.get("items") is False:
                raise ValueError(f"Reference exceeds array contract: {pointer}")
            else:
                return None
        elif current.get("type") == "object":
            if current.get("patternProperties"):
                return None
            if current.get("additionalProperties") is False:
                raise ValueError(f"Reference path does not exist in output contract: {pointer}")
            additional = current.get("additionalProperties")
            if isinstance(additional, dict):
                current = additional
            else:
                return None
        elif isinstance(current.get("type"), str) and current.get("type") in {
            "string",
            "integer",
            "number",
            "boolean",
            "null",
        }:
            raise ValueError(f"Cannot traverse scalar output contract: {pointer}")
        else:
            return None
    return current


def compatible_types(source: dict | None, target: dict | None) -> bool:
    """Reject provably incompatible types without guessing underspecified contracts."""
    source_type = (source or {}).get("type")
    target_type = (target or {}).get("type")
    if not source_type or not target_type:
        return True
    source_types = set(source_type if isinstance(source_type, list) else [source_type])
    target_types = set(target_type if isinstance(target_type, list) else [target_type])
    if "integer" in source_types:
        source_types.add("number")
    if "integer" in target_types:
        target_types.add("number")
    return bool(source_types & target_types)
