"""Thread safety utilities.

This module provides:
- TimeoutLock: Lock with configurable timeout to prevent deadlocks

Usage:
    from shared.threading_utils import TimeoutLock

    lock = TimeoutLock(timeout=5.0, name="my_lock")
    with lock:
        do_work()
"""

from __future__ import annotations

import threading
from typing import Any, Optional


class TimeoutLock:
    """Lock with configurable timeout to prevent deadlocks.

    Raises TimeoutError if lock cannot be acquired within timeout.

    Args:
        timeout: Maximum time to wait for lock (seconds)
        name: Name for this lock (used in error messages)
    """

    def __init__(self, timeout: float = 5.0, name: str = "unnamed") -> None:
        self._lock = threading.Lock()
        self._timeout = timeout
        self._name = name

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """Acquire the lock with timeout."""
        actual_timeout = timeout if timeout is not None else self._timeout

        if blocking and actual_timeout > 0:
            result = self._lock.acquire(blocking=True, timeout=actual_timeout)
            if not result:
                raise TimeoutError(
                    f"Failed to acquire lock '{self._name}' within {actual_timeout}s"
                )
            return result
        else:
            return self._lock.acquire(blocking, -1 if timeout is None else timeout)

    def release(self) -> None:
        """Release the lock."""
        self._lock.release()

    def __enter__(self) -> "TimeoutLock":
        self.acquire()
        return self

    def __exit__(self, *args: Any) -> None:
        self.release()

    def locked(self) -> bool:
        """Check if lock is currently held."""
        return self._lock.locked()


__all__ = ["TimeoutLock"]
