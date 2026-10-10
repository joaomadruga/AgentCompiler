"""Conservative nominal typing for JSON-carried Pydantic action contracts."""

from __future__ import annotations

import json
from types import UnionType
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel, TypeAdapter


def unwrap(annotation: Any) -> Any:
    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    return annotation


def branches(annotation: Any) -> tuple[Any, ...]:
    annotation = unwrap(annotation)
    if get_origin(annotation) in (Union, UnionType):
        return tuple(branch for item in get_args(annotation) for branch in branches(item))
    return (annotation,)


def type_name(annotation: Any) -> str:
    annotation = unwrap(annotation)
    if get_origin(annotation) in (Union, UnionType):
        return " | ".join(type_name(item) for item in get_args(annotation))
    if isinstance(annotation, type):
        return f"{annotation.__module__}.{annotation.__qualname__}"
    return str(annotation)


def assignable(source: Any, target: Any) -> bool:
    """Every possible source branch must fit at least one target branch."""
    return all(
        any(_assignable(left, right) for right in branches(target)) for left in branches(source)
    )


def _assignable(source: Any, target: Any) -> bool:
    source, target = unwrap(source), unwrap(target)
    if target is Any or source == target:
        return True
    if source is Any:
        return False
    source_origin, target_origin = get_origin(source), get_origin(target)
    if source_origin is Literal:
        values = get_args(source)
        if target_origin is Literal:
            return all(any(type(v) is type(t) and v == t for t in get_args(target)) for v in values)
        return all(_assignable(type(value), target) for value in values)
    if target_origin is Literal:
        return False
    if isinstance(source, type) and isinstance(target, type):
        if issubclass(source, BaseModel) and issubclass(target, BaseModel):
            return issubclass(source, target)
        # Python's bool subclasses int, but a JSON boolean is not a numeric value.
        return source is int and target is float
    if source_origin == target_origin and source_origin in (list, dict):
        left, right = get_args(source), get_args(target)
        return len(left) == len(right) and all(assignable(a, b) for a, b in zip(left, right))
    if source_origin is tuple and target_origin is tuple:
        left, right = get_args(source), get_args(target)
        if len(right) == 2 and right[1] is Ellipsis:
            items = left[:1] if len(left) == 2 and left[1] is Ellipsis else left
            return all(assignable(item, right[0]) for item in items)
        return (
            len(left) == len(right)
            and Ellipsis not in left
            and all(assignable(a, b) for a, b in zip(left, right))
        )
    return False


def type_at_pointer(annotation: Any, pointer: str) -> Any:
    """Resolve a path present in every branch; ambiguous branches remain a union."""
    tokens = [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]
    current = annotation
    for token in tokens:
        resolved = []
        for item in branches(current):
            origin, args = get_origin(item), get_args(item)
            if isinstance(item, type) and issubclass(item, BaseModel):
                field = item.model_fields.get(token)
                if field is None:
                    raise ValueError(
                        f"Typed reference path is not available in every branch: {pointer}"
                    )
                resolved.append(field.rebuild_annotation())
            elif (
                origin in (list, tuple)
                and token.isdigit()
                and (token == "0" or not token.startswith("0"))
            ):
                if origin is list or (len(args) == 2 and args[1] is Ellipsis):
                    resolved.append(args[0])
                elif int(token) < len(args):
                    resolved.append(args[int(token)])
                else:
                    raise ValueError(f"Typed tuple reference exceeds its contract: {pointer}")
            elif origin is dict and args[0] is str:
                resolved.append(args[1])
            else:
                raise ValueError(f"Cannot resolve typed reference path: {pointer}")
        current = resolved[0] if len(resolved) == 1 else Union[tuple(resolved)]
    return current


def validate_json_type(annotation: Any, value: Any) -> Any:
    """Strict JSON validation also runs custom Pydantic validators."""
    return TypeAdapter(annotation).validate_json(json.dumps(value, allow_nan=False), strict=True)


def validate_input_model(model: type[BaseModel], inputs: dict, sources: dict[str, Any]) -> dict:
    values = {}
    for name, value in inputs.items():
        field = model.model_fields.get(name)
        if field is None:
            values[name] = value  # The model enforces its extra-field policy.
            continue
        annotation = sources.get(name, field.rebuild_annotation())
        values[name] = validate_json_type(annotation, value)
    validated = model.model_validate(values, strict=True)
    # A base-typed consumer sees its own declared fields, not undeclared subclass fields.
    projected = validated.model_dump_json()
    # Existing subtype instances can bypass base-field validators in Pydantic.
    # Reparse the consumer projection so its own constraints always run.
    return model.model_validate_json(projected, strict=True).model_dump(mode="json")


def contract_catalog(annotation: Any) -> dict:
    models: dict[str, dict] = {}

    def visit(item: Any) -> None:
        item = unwrap(item)
        if isinstance(item, type) and issubclass(item, BaseModel):
            name = type_name(item)
            if name in models:
                return
            models[name] = {
                "bases": [
                    type_name(base)
                    for base in item.__mro__[1:]
                    if issubclass(base, BaseModel) and base is not BaseModel
                ],
                "fields": {
                    key: type_name(field.rebuild_annotation())
                    for key, field in item.model_fields.items()
                },
            }
            for field in item.model_fields.values():
                visit(field.annotation)
        else:
            for arg in get_args(item):
                visit(arg)

    visit(annotation)
    return {"type": type_name(annotation), "models": models}


def check_model_contract(annotation: Any) -> None:
    """Keep JSON binding names unambiguous; unsupported aliases fail registration."""
    seen: set[type] = set()

    def visit(item: Any) -> None:
        if get_origin(item) is Annotated:
            visit(get_args(item)[0])
        elif isinstance(item, type) and issubclass(item, BaseModel):
            if item in seen:
                return
            seen.add(item)
            if item.__pydantic_root_model__:
                raise ValueError("Typed contracts require object models; RootModel is unsupported.")
            item.model_rebuild()
            for name, field in item.model_fields.items():
                if field.alias or field.validation_alias or field.serialization_alias:
                    raise ValueError(f"Typed contracts do not support field aliases: {name}")
                if field.exclude:
                    raise ValueError(f"Typed contract fields cannot be excluded: {name}")
                visit(field.annotation)
        else:
            for arg in get_args(item):
                visit(arg)

    visit(annotation)
