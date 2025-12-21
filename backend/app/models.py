from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    JSON,
    TIMESTAMP,
    BigInteger,
    ForeignKey,
    text,
)
from sqlalchemy.orm import relationship

from .db import Base


class Instance(Base):
    __tablename__ = "instances"

    id = Column(Integer, primary_key=True, index=True)
    cloud_instance_id = Column(String(64), unique=True, nullable=False)
    cloud_provider = Column(String(16), nullable=False)
    account_id = Column(String(64))
    region = Column(String(32))
    instance_type = Column(String(32))
    environment = Column(String(32))
    tags = Column(JSON)
    hourly_cost = Column(Numeric(10, 4))
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text("NOW()")
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
    )

    metrics = relationship("Metric", back_populates="instance")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(BigInteger, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("instances.id"))
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    cpu_utilization = Column(Numeric(5, 2))
    mem_utilization = Column(Numeric(5, 2))
    network_in_bytes = Column(BigInteger)
    network_out_bytes = Column(BigInteger)

    instance = relationship("Instance", back_populates="metrics")
