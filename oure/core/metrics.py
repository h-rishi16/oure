"""
OURE Performance Metrics Manager
================================
"""

from prometheus_client import Counter, Histogram, Summary

# 1. Throughput Metrics
SATELLITES_PROPAGATED = Counter(
    "oure_satellites_propagated_total",
    "Total number of satellite trajectories propagated",
    ["propagator_type"],
)

# 2. Latency Metrics
RISK_CALCULATION_DURATION = Histogram(
    "oure_risk_calculation_seconds",
    "Time spent calculating Pc for a conjunction",
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)

# 3. Task Metrics
SCREENING_TASK_DURATION = Summary(
    "oure_screening_task_seconds",
    "Time spent on a full fleet screening background task",
)


class MetricsManager:
    """Helper to track engine performance."""

    @staticmethod
    def record_propagation(count: int, p_type: str = "numerical") -> None:
        SATELLITES_PROPAGATED.labels(propagator_type=p_type).inc(count)

    @staticmethod
    def record_risk_duration(duration: float) -> None:
        RISK_CALCULATION_DURATION.observe(duration)
