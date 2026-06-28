"""Console trace logging for AskAI pipeline (server CMD output)."""

from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from typing import Iterator

from config import get_settings


def is_verbose() -> bool:
    return get_settings().askai_verbose


def vlog(message: str) -> None:
    if is_verbose():
        print(f"[AskAI] {message}", flush=True)


def vlog_block(title: str, body: str, max_chars: int = 4000) -> None:
    if not is_verbose():
        return
    print(f"[AskAI] --- {title} ---", flush=True)
    text = body if len(body) <= max_chars else body[:max_chars] + "\n... (truncated)"
    print(text, flush=True)
    print("[AskAI] ---", flush=True)


def vlog_error(message: str, exc: BaseException | None = None) -> None:
    print(f"[AskAI] ERROR: {message}", flush=True, file=sys.stderr)
    if exc is not None and is_verbose():
        print(f"[AskAI]   {type(exc).__name__}: {exc}", flush=True, file=sys.stderr)


@contextmanager
def vlog_step(label: str) -> Iterator[None]:
    if not is_verbose():
        yield
        return
    started = time.perf_counter()
    vlog(f">> {label} ...")
    try:
        yield
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000
        vlog(f"<< {label} FAILED ({elapsed_ms:.0f} ms)")
        raise
    else:
        elapsed_ms = (time.perf_counter() - started) * 1000
        vlog(f"<< {label} OK ({elapsed_ms:.0f} ms)")
