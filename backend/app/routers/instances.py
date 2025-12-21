from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..schemas import InstanceOut, MetricOut

router = APIRouter(prefix="/instances", tags=["instances"])


@router.get("", response_model=List[InstanceOut])
def list_instances(
    db: Session = Depends(get_db),
    environment: str | None = Query(None, description="Filter by environment (prod/dev)"),
):
    query = db.query(models.Instance)
    if environment:
        query = query.filter(models.Instance.environment == environment)
    instances = query.order_by(models.Instance.id).all()
    return instances


@router.get("/{instance_id}", response_model=InstanceOut)
def get_instance(
    instance_id: int,
    db: Session = Depends(get_db),
):
    inst = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    return inst


@router.get("/{instance_id}/metrics", response_model=List[MetricOut])
def get_instance_metrics(
    instance_id: int,
    days: int = Query(7, ge=1, le=30, description="Lookback window in days"),
    db: Session = Depends(get_db),
):
    inst = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")

    now = datetime.now(timezone.utc)
    start_ts = now - timedelta(days=days)

    metrics = (
        db.query(models.Metric)
        .filter(
            models.Metric.instance_id == instance_id,
            models.Metric.timestamp >= start_ts,
        )
        .order_by(models.Metric.timestamp.asc())
        .all()
    )
    return metrics
