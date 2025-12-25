from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class InstanceBase(BaseModel):
    cloud_instance_id: str
    cloud_provider: str
    account_id: Optional[str] = None
    region: Optional[str] = None
    instance_type: Optional[str] = None
    environment: Optional[str] = None
    hourly_cost: Optional[float] = None
    tags: Optional[dict] = None


class InstanceOut(InstanceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 (instead of orm_mode=True)


class MetricOut(BaseModel):
    timestamp: datetime
    cpu_utilization: Optional[float] = None
    mem_utilization: Optional[float] = None
    network_in_bytes: Optional[int] = None
    network_out_bytes: Optional[int] = None

    class Config:
        from_attributes = True


class RecommendationOut(BaseModel):
    instance_id: int
    cloud_instance_id: str
    environment: Optional[str] = None
    region: Optional[str] = None
    instance_type: Optional[str] = None
    hourly_cost: Optional[float] = None
    action: str  # "keep" or "downsize"
    confidence_downsize: float
    projected_monthly_savings: float
    model_version: str
    reasons: List[str]

    class Config:
        from_attributes = True


class RightSizingActionCreate(BaseModel):
    instance_id: int
    new_instance_type: str
    cloud_provider: str = "aws"
    cloud_instance_id: Optional[str] = None
    region: Optional[str] = None


class RightSizingActionOut(BaseModel):
    id: int
    instance_id: int
    cloud_provider: str
    cloud_instance_id: str
    region: Optional[str] = None
    old_instance_type: Optional[str] = None
    new_instance_type: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    requested_at: datetime
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True
