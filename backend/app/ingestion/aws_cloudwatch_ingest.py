"""
AWS CloudWatch metrics ingestion for Cloud Cost Optimizer.

Pulls EC2 instance metrics from AWS CloudWatch and stores them in the database.

Configuration:
    - AWS_REGION: AWS region (e.g., us-west-2)
    - AWS_INSTANCE_IDS: Comma-separated EC2 instance IDs (e.g., i-0123...,i-0456...)

Usage:
    export AWS_REGION=us-west-2
    export AWS_INSTANCE_IDS=i-0123456789abcdef0,i-0fedcba9876543210
    cd backend
    python -m app.ingestion.aws_cloudwatch_ingest
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import Instance, Metric

logger = logging.getLogger(__name__)


def get_cloudwatch_client(region_name: str):
    """
    Create and return a boto3 CloudWatch client.
    
    Args:
        region_name: AWS region name (e.g., 'us-west-2')
        
    Returns:
        boto3 CloudWatch client
        
    Raises:
        NoCredentialsError: If AWS credentials are not configured
    """
    try:
        client = boto3.client("cloudwatch", region_name=region_name)
        return client
    except NoCredentialsError:
        raise ValueError(
            "AWS credentials not found. Please configure AWS_ACCESS_KEY_ID and "
            "AWS_SECRET_ACCESS_KEY, or use ~/.aws/credentials"
        )
    except Exception as e:
        raise ValueError(f"Failed to create CloudWatch client: {e}")


def fetch_ec2_metrics_for_instance(
    cloudwatch,
    instance_id: str,
    start_time: datetime,
    end_time: datetime,
) -> List[Dict]:
    """
    Fetch EC2 metrics from CloudWatch for a specific instance.
    
    Fetches:
    - CPUUtilization (Average)
    - NetworkIn (Sum)
    - NetworkOut (Sum)
    
    Args:
        cloudwatch: boto3 CloudWatch client
        instance_id: EC2 instance ID (e.g., 'i-0123456789abcdef0')
        start_time: Start time for metrics (UTC)
        end_time: End time for metrics (UTC)
        
    Returns:
        List of datapoints with structure:
        [
            {
                "timestamp": datetime,
                "cpu_utilization": float,
                "network_in_bytes": int,
                "network_out_bytes": int,
            },
            ...
        ]
    """
    datapoints_by_time = {}
    
    # Fetch CPUUtilization (Average)
    try:
        cpu_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,  # 1 hour
            Statistics=["Average"],
        )
        
        for datapoint in cpu_response.get("Datapoints", []):
            ts = datapoint["Timestamp"].replace(tzinfo=timezone.utc)
            if ts not in datapoints_by_time:
                datapoints_by_time[ts] = {
                    "timestamp": ts,
                    "cpu_utilization": None,
                    "network_in_bytes": None,
                    "network_out_bytes": None,
                }
            datapoints_by_time[ts]["cpu_utilization"] = float(datapoint["Average"])
    except ClientError as e:
        logger.warning(
            f"Failed to fetch CPUUtilization for {instance_id}: {e.response.get('Error', {}).get('Message', str(e))}"
        )
    
    # Fetch NetworkIn (Sum)
    try:
        network_in_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="NetworkIn",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,  # 1 hour
            Statistics=["Sum"],
        )
        
        for datapoint in network_in_response.get("Datapoints", []):
            ts = datapoint["Timestamp"].replace(tzinfo=timezone.utc)
            if ts not in datapoints_by_time:
                datapoints_by_time[ts] = {
                    "timestamp": ts,
                    "cpu_utilization": None,
                    "network_in_bytes": None,
                    "network_out_bytes": None,
                }
            # NetworkIn is in bytes, sum over the hour
            datapoints_by_time[ts]["network_in_bytes"] = int(datapoint["Sum"])
    except ClientError as e:
        logger.warning(
            f"Failed to fetch NetworkIn for {instance_id}: {e.response.get('Error', {}).get('Message', str(e))}"
        )
    
    # Fetch NetworkOut (Sum)
    try:
        network_out_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="NetworkOut",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,  # 1 hour
            Statistics=["Sum"],
        )
        
        for datapoint in network_out_response.get("Datapoints", []):
            ts = datapoint["Timestamp"].replace(tzinfo=timezone.utc)
            if ts not in datapoints_by_time:
                datapoints_by_time[ts] = {
                    "timestamp": ts,
                    "cpu_utilization": None,
                    "network_in_bytes": None,
                    "network_out_bytes": None,
                }
            # NetworkOut is in bytes, sum over the hour
            datapoints_by_time[ts]["network_out_bytes"] = int(datapoint["Sum"])
    except ClientError as e:
        logger.warning(
            f"Failed to fetch NetworkOut for {instance_id}: {e.response.get('Error', {}).get('Message', str(e))}"
        )
    
    # Convert to list and sort by timestamp
    datapoints = sorted(datapoints_by_time.values(), key=lambda x: x["timestamp"])
    
    # Fill missing values with 0 or None
    for dp in datapoints:
        if dp["cpu_utilization"] is None:
            dp["cpu_utilization"] = 0.0
        if dp["network_in_bytes"] is None:
            dp["network_in_bytes"] = 0
        if dp["network_out_bytes"] is None:
            dp["network_out_bytes"] = 0
    
    return datapoints


def upsert_metrics_for_instance(
    db: Session, instance: Instance, datapoints: List[Dict]
) -> int:
    """
    Upsert metrics for an instance into the database.
    
    For each datapoint, checks if a metric already exists for (instance_id, timestamp).
    If not, creates a new Metric row.
    
    Args:
        db: SQLAlchemy session
        instance: Instance object
        datapoints: List of metric datapoints from fetch_ec2_metrics_for_instance
        
    Returns:
        Number of metrics inserted/updated
    """
    inserted_count = 0
    
    for dp in datapoints:
        # Check if metric already exists
        existing = (
            db.query(Metric)
            .filter(
                Metric.instance_id == instance.id,
                Metric.timestamp == dp["timestamp"],
            )
            .first()
        )
        
        if existing:
            # Update existing metric
            existing.cpu_utilization = dp["cpu_utilization"]
            existing.network_in_bytes = dp["network_in_bytes"]
            existing.network_out_bytes = dp["network_out_bytes"]
            # mem_utilization is None for CloudWatch (we don't fetch it)
        else:
            # Create new metric
            metric = Metric(
                instance_id=instance.id,
                timestamp=dp["timestamp"],
                cpu_utilization=dp["cpu_utilization"],
                mem_utilization=None,  # CloudWatch doesn't provide memory metrics for EC2
                network_in_bytes=dp["network_in_bytes"],
                network_out_bytes=dp["network_out_bytes"],
            )
            db.add(metric)
            inserted_count += 1
    
    db.commit()
    return inserted_count


def ingest_aws_cloudwatch_metrics(lookback_hours: int = 24) -> None:
    """
    Main orchestration function to ingest AWS CloudWatch metrics.
    
    Reads AWS_REGION and AWS_INSTANCE_IDS from environment variables,
    pulls metrics from CloudWatch, and writes them to the metrics table.
    
    Args:
        lookback_hours: Number of hours to look back for metrics (default: 24)
        
    Raises:
        ValueError: If required environment variables are missing
    """
    # Read configuration from environment
    region = os.getenv("AWS_REGION")
    if not region:
        raise ValueError(
            "AWS_REGION environment variable is required. "
            "Example: export AWS_REGION=us-west-2"
        )
    
    instance_ids_str = os.getenv("AWS_INSTANCE_IDS")
    if not instance_ids_str:
        raise ValueError(
            "AWS_INSTANCE_IDS environment variable is required. "
            "Example: export AWS_INSTANCE_IDS=i-0123...,i-0456..."
        )
    
    # Parse instance IDs
    instance_ids = [s.strip() for s in instance_ids_str.split(",") if s.strip()]
    if not instance_ids:
        raise ValueError("AWS_INSTANCE_IDS is empty or invalid")
    
    print(f"\n{'=' * 60}")
    print(f"📊 AWS CloudWatch Metrics Ingestion")
    print(f"{'=' * 60}")
    print(f"Region: {region}")
    print(f"Instance IDs: {', '.join(instance_ids)}")
    print(f"Lookback: {lookback_hours} hours")
    print(f"{'=' * 60}\n")
    
    # Create CloudWatch client
    try:
        cloudwatch = get_cloudwatch_client(region)
        print("✅ CloudWatch client initialized")
    except ValueError as e:
        print(f"❌ Error: {e}")
        return
    
    # Calculate time range
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=lookback_hours)
    
    # Open database session
    db: Session = SessionLocal()
    processed_count = 0
    total_metrics_inserted = 0
    
    try:
        for instance_id in instance_ids:
            print(f"\n📦 Processing instance: {instance_id}")
            
            # Find matching Instance in database
            instance = (
                db.query(Instance)
                .filter(
                    Instance.cloud_instance_id == instance_id,
                    Instance.cloud_provider == "aws",
                )
                .first()
            )
            
            if not instance:
                # Option: Create a new Instance row with minimal info
                # This allows ingestion even if instance wasn't pre-registered
                print(f"   ⚠️  No Instance row found for {instance_id}, creating new entry...")
                instance = Instance(
                    cloud_instance_id=instance_id,
                    cloud_provider="aws",
                    region=region,
                    environment="prod",  # Default assumption
                    tags={"ingested_from": "aws_cloudwatch_ingest"},
                )
                db.add(instance)
                db.commit()
                db.refresh(instance)
                print(f"   ✅ Created Instance row (id: {instance.id})")
            
            # Fetch metrics from CloudWatch
            print(f"   🔄 Fetching metrics from CloudWatch...")
            try:
                datapoints = fetch_ec2_metrics_for_instance(
                    cloudwatch, instance_id, start_time, end_time
                )
                print(f"   ✅ Retrieved {len(datapoints)} datapoints")
            except Exception as e:
                logger.error(f"Error fetching metrics for {instance_id}: {e}")
                print(f"   ❌ Failed to fetch metrics: {e}")
                continue
            
            if not datapoints:
                print(f"   ⚠️  No metrics found for {instance_id} in the specified time range")
                continue
            
            # Upsert metrics into database
            print(f"   💾 Writing metrics to database...")
            inserted = upsert_metrics_for_instance(db, instance, datapoints)
            total_metrics_inserted += inserted
            print(f"   ✅ Inserted/updated {inserted} metrics")
            processed_count += 1
        
        # Summary
        print(f"\n{'=' * 60}")
        print(f"✅ Ingested CloudWatch metrics for {processed_count} instance(s) (last {lookback_hours}h)")
        print(f"   Total metrics inserted/updated: {total_metrics_inserted}")
        print(f"{'=' * 60}\n")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during ingestion: {e}", exc_info=True)
        print(f"\n❌ Error during ingestion: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    try:
        ingest_aws_cloudwatch_metrics()
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nPlease set the following environment variables:")
        print("  export AWS_REGION=us-west-2")
        print("  export AWS_INSTANCE_IDS=i-0123456789abcdef0,i-0fedcba9876543210")
        exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        exit(1)



