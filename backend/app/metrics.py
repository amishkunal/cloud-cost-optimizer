"""
Minimal in-memory metrics for Cloud Cost Optimizer.

Purpose: provide resume/demo-friendly observability without extra infra.
Exports Prometheus-style text at /metrics.
"""

from __future__ import annotations

import math
import threading
import time
from collections import Counter, defaultdict, deque
from typing import Deque, Dict, Tuple


def _now_ms() -> float:
    return time.perf_counter() * 1000.0


class MetricsStore:
    def __init__(self, latency_window_size: int = 500):
        self._lock = threading.Lock()
        self._latency_window_size = latency_window_size

        # (method, path, status) -> count
        self.http_requests_total: Counter[Tuple[str, str, int]] = Counter()

        # (method, path) -> deque of last N durations in ms
        self.http_request_duration_ms_window: Dict[Tuple[str, str], Deque[float]] = defaultdict(
            lambda: deque(maxlen=self._latency_window_size)
        )

        # result -> count (verified/mismatch/error)
        self.verify_actions_total: Counter[str] = Counter()

    def observe_http(self, method: str, path: str, status: int, duration_ms: float) -> None:
        with self._lock:
            self.http_requests_total[(method, path, int(status))] += 1
            self.http_request_duration_ms_window[(method, path)].append(float(duration_ms))

    def inc_verify_result(self, result: str) -> None:
        with self._lock:
            self.verify_actions_total[result] += 1

    def snapshot_prometheus(self) -> str:
        with self._lock:
            req_total = dict(self.http_requests_total)
            lat_windows = {k: list(v) for k, v in self.http_request_duration_ms_window.items()}
            verify_total = dict(self.verify_actions_total)

        lines: list[str] = []

        # http_requests_total
        lines.append("# HELP ccopt_http_requests_total Total HTTP requests by method/path/status")
        lines.append("# TYPE ccopt_http_requests_total counter")
        for (method, path, status), count in sorted(req_total.items()):
            lines.append(
                f'ccopt_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
            )

        # latency summaries (rolling)
        lines.append("# HELP ccopt_http_request_duration_ms Rolling request latency summary (ms)")
        lines.append("# TYPE ccopt_http_request_duration_ms gauge")
        for (method, path), vals in sorted(lat_windows.items()):
            if not vals:
                continue
            vals_sorted = sorted(vals)
            n = len(vals_sorted)
            p50 = vals_sorted[int(0.50 * (n - 1))]
            p95 = vals_sorted[int(0.95 * (n - 1))]
            p99 = vals_sorted[int(0.99 * (n - 1))]
            avg = sum(vals_sorted) / n
            mx = max(vals_sorted)

            def emit(stat: str, value: float) -> None:
                if math.isnan(value) or math.isinf(value):
                    return
                lines.append(
                    f'ccopt_http_request_duration_ms{{method="{method}",path="{path}",stat="{stat}"}} {value:.3f}'
                )

            emit("p50", p50)
            emit("p95", p95)
            emit("p99", p99)
            emit("avg", avg)
            emit("max", mx)
            emit("n", float(n))

        # verify_actions_total
        lines.append("# HELP ccopt_verify_actions_total Verification attempts by result")
        lines.append("# TYPE ccopt_verify_actions_total counter")
        for result, count in sorted(verify_total.items()):
            lines.append(f'ccopt_verify_actions_total{{result="{result}"}} {count}')

        return "\n".join(lines) + "\n"


METRICS = MetricsStore()


class RequestTimer:
    def __init__(self):
        self._start_ms = _now_ms()

    def elapsed_ms(self) -> float:
        return _now_ms() - self._start_ms


