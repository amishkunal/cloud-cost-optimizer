"""
Metrics router for Cloud Cost Optimizer.

Exposes Prometheus-style text metrics at /metrics.
"""

from fastapi import APIRouter, Response

from ..metrics import METRICS

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics() -> Response:
    payload = METRICS.snapshot_prometheus()
    return Response(content=payload, media_type="text/plain; version=0.0.4")


