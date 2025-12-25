"""
Actions router for Cloud Cost Optimizer.

Tracks right-sizing actions and verifies whether they were applied in AWS.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..metrics import METRICS
from ..models import Instance, RightSizingAction
from ..schemas import RightSizingActionCreate, RightSizingActionOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/actions", tags=["actions"])


def _get_ec2_instance_type(cloud_instance_id: str, region: str) -> str:
    try:
        ec2 = boto3.client("ec2", region_name=region)
        resp = ec2.describe_instances(InstanceIds=[cloud_instance_id])
        reservations = resp.get("Reservations", [])
        instances = reservations[0].get("Instances", []) if reservations else []
        if not instances:
            raise ValueError(f"Instance not found in AWS: {cloud_instance_id}")
        return str(instances[0].get("InstanceType"))
    except NoCredentialsError:
        raise ValueError("AWS credentials not configured for verification")
    except (ClientError, BotoCoreError) as e:
        raise ValueError(f"AWS verification failed: {e}")


@router.get("", response_model=List[RightSizingActionOut])
def list_actions(db: Session = Depends(get_db), instance_id: Optional[int] = None):
    q = db.query(RightSizingAction).order_by(RightSizingAction.id.desc())
    if instance_id is not None:
        q = q.filter(RightSizingAction.instance_id == instance_id)
    return q.all()


@router.post("", response_model=RightSizingActionOut)
def create_action(payload: RightSizingActionCreate, db: Session = Depends(get_db)):
    inst = db.query(Instance).filter(Instance.id == payload.instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")

    cloud_instance_id = payload.cloud_instance_id or inst.cloud_instance_id
    region = payload.region or inst.region
    if not cloud_instance_id:
        raise HTTPException(status_code=400, detail="cloud_instance_id is required")
    if not region:
        raise HTTPException(status_code=400, detail="region is required (instance missing region)")

    # Best-effort: capture current instance type from AWS to avoid stale DB values.
    old_instance_type = inst.instance_type
    if payload.cloud_provider == "aws":
        try:
            old_instance_type = _get_ec2_instance_type(cloud_instance_id, region)
            # Keep DB roughly in sync with reality (best-effort, not critical)
            inst.instance_type = old_instance_type
            db.add(inst)
        except Exception:
            # Fall back to DB value if AWS creds/permissions aren't available
            old_instance_type = inst.instance_type

    now = datetime.now(timezone.utc)
    initial_status = "pending"
    initial_verified_at = None
    if old_instance_type and payload.new_instance_type and old_instance_type == payload.new_instance_type:
        initial_status = "verified"
        initial_verified_at = now

    action = RightSizingAction(
        instance_id=inst.id,
        cloud_provider=payload.cloud_provider,
        cloud_instance_id=cloud_instance_id,
        region=region,
        old_instance_type=old_instance_type,
        new_instance_type=payload.new_instance_type,
        status=initial_status,
        verified_at=initial_verified_at,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


@router.post("/{action_id}/verify", response_model=RightSizingActionOut)
def verify_action(action_id: int, db: Session = Depends(get_db)):
    action = db.query(RightSizingAction).filter(RightSizingAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.cloud_provider != "aws":
        raise HTTPException(status_code=400, detail="Only AWS verification is supported")
    if not action.region:
        raise HTTPException(status_code=400, detail="Action is missing region")

    try:
        current_type = _get_ec2_instance_type(action.cloud_instance_id, action.region)
        # Keep instance row in sync with reality (useful for UI + future actions)
        inst = db.query(Instance).filter(Instance.id == action.instance_id).first()
        if inst:
            inst.instance_type = current_type
            db.add(inst)
        if action.new_instance_type and current_type == action.new_instance_type:
            action.status = "verified"
            action.error_message = None
            action.verified_at = datetime.now(timezone.utc)
            METRICS.inc_verify_result("verified")
        else:
            action.status = "mismatch"
            action.error_message = (
                f"Expected {action.new_instance_type}, found {current_type}"
            )
            action.verified_at = None
            METRICS.inc_verify_result("mismatch")
    except ValueError as e:
        action.status = "error"
        action.error_message = str(e)
        action.verified_at = None
        METRICS.inc_verify_result("error")
    except Exception as e:
        logger.error(f"Unexpected verify error: {e}", exc_info=True)
        action.status = "error"
        action.error_message = f"Unexpected verification error: {e}"
        action.verified_at = None
        METRICS.inc_verify_result("error")

    db.add(action)
    db.commit()
    db.refresh(action)
    return action


