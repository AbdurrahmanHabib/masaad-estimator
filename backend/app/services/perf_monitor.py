"""Performance monitoring utilities for Masaad Estimator pipeline."""
import time
import logging
import threading
import functools
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("masaad-api.perf")


def timed(func: Callable) -> Callable:
    """
    Decorator that measures and logs execution time for synchronous functions.

    Usage::

        @timed
        def my_function():
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.debug(
                "function timed",
                extra={
                    "function": func.__qualname__,
                    "module": func.__module__,
                    "duration_ms": duration_ms,
                },
            )
    return wrapper


def timed_async(func: Callable) -> Callable:
    """
    Decorator that measures and logs execution time for async functions.

    Usage::

        @timed_async
        async def my_async_function():
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.debug(
                "async function timed",
                extra={
                    "function": func.__qualname__,
                    "module": func.__module__,
                    "duration_ms": duration_ms,
                },
            )
    return wrapper


class PerformanceTracker:
    """
    Thread-safe in-memory tracker for pipeline-level metrics.

    Tracks:
    - Total estimates processed
    - Cumulative and average pipeline duration
    - Slowest node across all estimates
    - Error count broken down by node name
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._estimates_processed: int = 0
        self._total_pipeline_duration_ms: float = 0.0
        self._node_durations: Dict[str, list] = {}   # node_name -> [duration_ms, ...]
        self._error_counts: Dict[str, int] = {}       # node_name -> count
        self._slowest_node: Optional[str] = None
        self._slowest_node_ms: float = 0.0

    # ------------------------------------------------------------------
    # Public write API
    # ------------------------------------------------------------------

    def record_estimate_complete(self, pipeline_duration_ms: float) -> None:
        """Call once when a full estimate pipeline finishes successfully."""
        with self._lock:
            self._estimates_processed += 1
            self._total_pipeline_duration_ms += pipeline_duration_ms

    def record_node_duration(self, node_name: str, duration_ms: float) -> None:
        """Record how long a single LangGraph node took."""
        with self._lock:
            if node_name not in self._node_durations:
                self._node_durations[node_name] = []
            self._node_durations[node_name].append(duration_ms)

            if duration_ms > self._slowest_node_ms:
                self._slowest_node_ms = duration_ms
                self._slowest_node = node_name

    def record_node_error(self, node_name: str) -> None:
        """Increment the error counter for a given node."""
        with self._lock:
            self._error_counts[node_name] = self._error_counts.get(node_name, 0) + 1

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------

    def get_metrics(self) -> Dict[str, Any]:
        """
        Return a snapshot of all collected metrics.

        Returns
        -------
        dict with keys:
            estimates_processed       : int
            avg_pipeline_duration_ms  : float  (0 if none processed)
            slowest_node              : str | None
            slowest_node_ms           : float
            error_count               : int   (total across all nodes)
            error_count_by_node       : dict  {node_name: count}
            node_avg_durations_ms     : dict  {node_name: avg_ms}
        """
        with self._lock:
            avg = (
                round(self._total_pipeline_duration_ms / self._estimates_processed, 2)
                if self._estimates_processed > 0
                else 0.0
            )

            node_avgs: Dict[str, float] = {}
            for node, durations in self._node_durations.items():
                node_avgs[node] = round(sum(durations) / len(durations), 2) if durations else 0.0

            total_errors = sum(self._error_counts.values())

            return {
                "estimates_processed": self._estimates_processed,
                "avg_pipeline_duration_ms": avg,
                "slowest_node": self._slowest_node,
                "slowest_node_ms": round(self._slowest_node_ms, 2),
                "error_count": total_errors,
                "error_count_by_node": dict(self._error_counts),
                "node_avg_durations_ms": node_avgs,
            }

    def reset(self) -> None:
        """Reset all counters (useful in tests)."""
        with self._lock:
            self._estimates_processed = 0
            self._total_pipeline_duration_ms = 0.0
            self._node_durations.clear()
            self._error_counts.clear()
            self._slowest_node = None
            self._slowest_node_ms = 0.0


# Module-level singleton — import this instance everywhere else.
tracker = PerformanceTracker()
