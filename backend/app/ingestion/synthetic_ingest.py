from datetime import datetime, timedelta, timezone
import random

from sqlalchemy.orm import Session

from ..db import SessionLocal, Base, engine   # ⬅️ add Base, engine
from ..models import Instance, Metric


def seed_synthetic_data(days: int = 7, instances: int = 100):
    # Ensure tables exist (for standalone script)
    Base.metadata.create_all(bind=engine)     # ⬅️ add this line

    db: Session = SessionLocal()

    # 1. Create synthetic instances
    for i in range(instances):
        inst = Instance(
            cloud_instance_id=f"i-synth-{i}",
            cloud_provider="aws",
            account_id="111111111111",
            region="us-west-2",
            instance_type="m5.large",
            environment="dev" if i % 2 == 0 else "prod",
            tags={"project": "ccopt-demo"},
            hourly_cost=0.096,
        )
        db.add(inst)
    db.commit()

    all_instances = db.query(Instance).all()

    # 2. Create synthetic hourly metrics
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    current = start
    while current <= now:
        for inst in all_instances:
            base_cpu = 10 if inst.environment == "dev" else 35
            cpu = base_cpu + random.uniform(-5, 10)
            mem = 20 + random.uniform(-5, 15)

            metric = Metric(
                instance_id=inst.id,
                timestamp=current,
                cpu_utilization=round(max(cpu, 0), 2),
                mem_utilization=round(max(mem, 0), 2),
                network_in_bytes=random.randint(10_000_000, 50_000_000),
                network_out_bytes=random.randint(10_000_000, 50_000_000),
            )
            db.add(metric)
        db.commit()
        current += timedelta(hours=1)

    db.close()
    print("Synthetic data seeded.")


if __name__ == "__main__":
    seed_synthetic_data()
