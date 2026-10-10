"""In-memory event tracing with optional callbacks and JSONL export."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import Field, JsonValue

from ..compiler.schemas import Contract

logger = logging.getLogger(__name__)


class ExecutionEvent(Contract):
    run_id: str
    kind: str
    timestamp: float = Field(default_factory=time.time)
    task_id: str | None = None
    data: dict[str, JsonValue] = Field(default_factory=dict)


class TraceRecorder:
    def __init__(self, callback: Callable[[ExecutionEvent], None] | None = None) -> None:
        self.events: list[ExecutionEvent] = []
        self.callback = callback

    def emit(self, event: ExecutionEvent) -> None:
        self.events.append(event)
        if self.callback:
            try:
                self.callback(event.model_copy(deep=True))
            except Exception:
                logger.exception("Trace callback failed; execution continues.")

    def write_jsonl(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "".join(event.model_dump_json() + "\n" for event in self.events), encoding="utf-8"
        )
