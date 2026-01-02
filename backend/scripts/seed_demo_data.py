"""
Demo data seeding script for Cloud Cost Optimizer.

Populates the database with synthetic instances and metrics for local development and presentations.
"""

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models import Instance, Metric, RightSizingAction


def generate_demo_data():
    """Generate and insert demo data into the database."""
    
    # Ask for confirmation
    print("\n" + "=" * 60)
    print("⚠️  WARNING: This will delete all existing instances and metrics!")
    print("=" * 60)
    response = input("Do you want to continue? (Y/n): ").strip().lower()
    
    if response not in ['y', 'yes', '']:
        print("❌ Seeding cancelled.")
        return
    
    # Use database session with proper cleanup
    db = SessionLocal()
    try:
        # Delete existing data
        print("\n🗑️  Clearing existing data...")
        db.query(RightSizingAction).delete()
        db.query(Metric).delete()
        db.query(Instance).delete()
        db.commit()
        print("✅ Existing data cleared.")
        
        # Configuration
        regions = ["us-west-2", "us-east-1"]
        instance_types = ["m5.large", "m5.xlarge", "t3.medium", "c5.large"]
        
        # Generate instances with specific distribution
        # 10 prod, 10 dev, 5 staging = 25 total
        instances = []
        instance_counter = 0
        
        # Production instances (10)
        for i in range(10):
            instance = Instance(
                cloud_instance_id=f"i-demo-{instance_counter:03d}",
                cloud_provider="aws",
                environment="prod",
                region=random.choice(regions),
                instance_type=random.choice(instance_types),
                hourly_cost=round(random.uniform(0.05, 0.20), 4),
                tags={"demo": "true", "seeded_by": "seed_demo_data.py"},
            )
            instances.append(instance)
            instance_counter += 1
        
        # Development instances (10)
        for i in range(10):
            instance = Instance(
                cloud_instance_id=f"i-demo-{instance_counter:03d}",
                cloud_provider="aws",
                environment="dev",
                region=random.choice(regions),
                instance_type=random.choice(instance_types),
                hourly_cost=round(random.uniform(0.05, 0.20), 4),
                tags={"demo": "true", "seeded_by": "seed_demo_data.py"},
            )
            instances.append(instance)
            instance_counter += 1
        
        # Staging instances (5)
        for i in range(5):
            instance = Instance(
                cloud_instance_id=f"i-demo-{instance_counter:03d}",
                cloud_provider="aws",
                environment="staging",
                region=random.choice(regions),
                instance_type=random.choice(instance_types),
                hourly_cost=round(random.uniform(0.05, 0.20), 4),
                tags={"demo": "true", "seeded_by": "seed_demo_data.py"},
            )
            instances.append(instance)
            instance_counter += 1
        
        # Bulk insert instances
        print(f"\n📦 Creating {len(instances)} demo instances...")
        db.bulk_save_objects(instances)
        db.commit()
        
        # Re-fetch instances with IDs
        instance_ids_map = {}
        for instance in instances:
            fetched = db.query(Instance).filter(
                Instance.cloud_instance_id == instance.cloud_instance_id
            ).first()
            if fetched:
                instance_ids_map[instance.cloud_instance_id] = fetched.id
        
        print("✅ Instances created.")
        
        # Generate metrics for each instance
        print("\n📊 Generating metrics (7 days of hourly data)...")
        now = datetime.now(timezone.utc)
        all_metrics = []
        
        for instance in instances:
            instance_id = instance_ids_map.get(instance.cloud_instance_id)
            if not instance_id:
                continue
            
            # Define base utilization ranges by environment
            if instance.environment == "prod":
                cpu_min, cpu_max = 40, 80
                mem_min, mem_max = 50, 80
            elif instance.environment == "dev":
                cpu_min, cpu_max = 5, 25
                mem_min, mem_max = 10, 30
            else:  # staging
                cpu_min, cpu_max = 20, 50
                mem_min, mem_max = 30, 50
            
            # Generate 7 days of hourly metrics (24 hours × 7 days = 168 metrics per instance)
            for day_offset in range(7):
                for hour_offset in range(24):
                    # Calculate timestamp: from 7 days ago to now, hourly
                    hours_ago = (6 - day_offset) * 24 + (23 - hour_offset)
                    timestamp = now - timedelta(hours=hours_ago)
                    
                    # Generate CPU and memory with correlation and noise
                    base_cpu = random.uniform(cpu_min, cpu_max)
                    base_mem = random.uniform(mem_min, mem_max)
                    
                    # Add correlation (high CPU often correlates with high memory)
                    correlation_factor = random.uniform(0.7, 1.0)
                    cpu_util = max(0, min(100, base_cpu + random.uniform(-5, 5)))
                    mem_util = max(0, min(100, base_mem + (base_cpu - cpu_min) / (cpu_max - cpu_min) * 10 * correlation_factor + random.uniform(-5, 5)))
                    
                    # Network traffic: utilization × 10⁶ bytes
                    # Convert utilization percentage to bytes (scaled for realism)
                    network_in_bytes = int(cpu_util * 1_000_000)  # CPU util % × 10⁶
                    network_out_bytes = int(mem_util * 1_000_000)  # Mem util % × 10⁶
                    
                    metric = Metric(
                        instance_id=instance_id,
                        timestamp=timestamp,
                        cpu_utilization=round(cpu_util, 2),
                        mem_utilization=round(mem_util, 2),
                        network_in_bytes=network_in_bytes,
                        network_out_bytes=network_out_bytes,
                    )
                    all_metrics.append(metric)
        
        # Bulk insert metrics
        print(f"   Inserting {len(all_metrics)} metric records...")
        db.bulk_save_objects(all_metrics)
        db.commit()
        print("✅ Metrics inserted.")
        
        # Count environment distribution
        env_counts = {}
        for instance in instances:
            env = instance.environment
            env_counts[env] = env_counts.get(env, 0) + 1
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ Demo data seeded successfully!")
        print("=" * 60)
        print(f"✅ Seeded {len(instances)} instances")
        print(f"✅ Inserted {len(all_metrics)} metrics (7 days hourly)")
        print(f"\nEnvironments: ", end="")
        env_str = ", ".join([f"{env}={count}" for env, count in sorted(env_counts.items())])
        print(env_str)
        print("=" * 60)
        
        print("\n📝 Next steps:")
        print("   1. Train the model: python -m app.ml.train_model")
        print("   2. Start the backend: uvicorn app.main:app --reload")
        print("   3. Visit /recommendations to see optimization suggestions")
        print("=" * 60 + "\n")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    generate_demo_data()
