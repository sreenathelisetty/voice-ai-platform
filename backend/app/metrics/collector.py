"""In-process latency accumulator."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricBucket:
    values: list[float] = field(default_factory=list)


class MetricsCollector:
    """Singleton accumulator for per-turn latency values."""

    _instance: MetricsCollector | None = None

    def __new__(cls) -> MetricsCollector:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = asyncio.Lock()
            cls._instance._buckets: dict[str, MetricBucket] = defaultdict(MetricBucket)
        return cls._instance

    async def record(self, metric_name: str, value_ms: float) -> None:
        async with self._lock:
            self._buckets[metric_name].values.append(value_ms)

    async def snapshot(self) -> dict[str, dict[str, float]]:
        """Return current p50/p95/p99 for each metric."""
        import numpy as np

        async with self._lock:
            result: dict[str, dict[str, float]] = {}
            for name, bucket in self._buckets.items():
                if not bucket.values:
                    continue
                arr = np.array(bucket.values)
                result[name] = {
                    "p50": float(np.percentile(arr, 50)),
                    "p95": float(np.percentile(arr, 95)),
                    "p99": float(np.percentile(arr, 99)),
                    "count": len(arr),
                    "mean": float(np.mean(arr)),
                }
        return result
