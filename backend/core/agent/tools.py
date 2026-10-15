"""Validated semantic retrieval with bounded workers and invocation records."""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextvars import copy_context
from dataclasses import dataclass
from typing import Callable

from apps.navigator.models import ToolExecution
from pydantic import ValidationError

from core.observability import event
from core.rag.retrieval import retrieve
from core.schemas import RetrievalRequest

_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="scholarship-tool")
_CAPACITY = threading.BoundedSemaphore(4)


@dataclass(frozen=True)
class Tool:
    name: str
    schema: type
    function: Callable


def _retrieval(payload):
    return retrieve(**payload.model_dump())


RETRIEVAL_TOOL = Tool("scholarship_retrieval", RetrievalRequest, _retrieval)


class ToolFailure(Exception):
    def __init__(self, code, name):
        self.code, self.name = code, name
        super().__init__(f"{name}: {code}")


def invoke(tool: Tool, arguments: dict, execution, timeout=None):
    """Invalid input is not retried. Transient tool failures get one retry."""
    try:
        payload = tool.schema.model_validate(arguments)
    except ValidationError:
        ToolExecution.objects.create(
            execution=execution,
            name=tool.name,
            status="FAILED",
            latency_ms=0,
            error_code="INVALID_TOOL_ARGUMENTS",
        )
        event("tool_call", tool=tool.name, status="INVALID_TOOL_ARGUMENTS")
        raise ToolFailure("INVALID_TOOL_ARGUMENTS", tool.name) from None
    timeout = float(os.getenv("TOOL_TIMEOUT_SECONDS", "30")) if timeout is None else timeout
    for attempt in range(1, 3):
        started = time.perf_counter()
        error = ""
        if not _CAPACITY.acquire(blocking=False):
            error = "TOOL_CAPACITY_EXCEEDED"
        else:

            def run():
                try:
                    return tool.function(payload)
                finally:
                    _CAPACITY.release()

            future = _POOL.submit(copy_context().run, run)
            try:
                result = future.result(timeout=timeout)
            except TimeoutError:
                # Do not release a running worker's slot prematurely.
                error = "TOOL_TIMEOUT"
            except Exception as exc:
                error = "INVALID_TOOL_ARGUMENTS" if isinstance(exc, ValueError) else "TOOL_FAILED"
        duration = (time.perf_counter() - started) * 1000
        ToolExecution.objects.create(
            execution=execution,
            name=tool.name,
            attempt=attempt,
            status="FAILED" if error else "SUCCESS",
            latency_ms=duration,
            error_code=error,
        )
        event(
            "tool_call",
            tool=tool.name,
            attempt=attempt,
            status=error or "SUCCESS",
            latency_ms=duration,
        )
        if not error:
            return result
        if error in ("INVALID_TOOL_ARGUMENTS", "TOOL_CAPACITY_EXCEEDED"):
            break
    raise ToolFailure(error, tool.name)
