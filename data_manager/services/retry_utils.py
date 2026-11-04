from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _attempts() -> int:
    try:
        return max(1, int(os.getenv("HTTP_RETRY_ATTEMPTS", "3")))
    except ValueError:
        return 3


def _base_delay() -> float:
    try:
        return max(0.1, float(os.getenv("HTTP_RETRY_BASE_DELAY_SEC", "1.0")))
    except ValueError:
        return 1.0


def retry_call(
    fn: Callable[[], T],
    *,
    label: str,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    attempts = _attempts()
    delay = _base_delay()
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except exceptions as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            sleep_for = delay * (2 ** (attempt - 1))
            logger.warning("%s failed (attempt %s/%s): %s; retry in %.1fs", label, attempt, attempts, exc, sleep_for)
            time.sleep(sleep_for)
    assert last_exc is not None
    raise last_exc
