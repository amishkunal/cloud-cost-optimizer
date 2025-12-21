"""
Feature engineering module for Cloud Cost Optimizer.

This module provides shared feature engineering logic used by both
training and inference (recommendations).
"""

from datetime import datetime, timedelta, timezone
from typing import Tuple

import pandas as pd
from sqlalchemy.orm import Session

from ..models import Instance, Metric


def extract_instance_type_family(instance_type: str) -> str:
    """Extract family prefix from instance type (e.g., 'm5.large' -> 'm5')."""
    if pd.isna(instance_type) or not instance_type:
        return "unknown"
    parts = str(instance_type).split(".")
    return parts[0] if parts else "unknown"


def compute_instance_features(
    session: Session,
    lookback_days: int = 7,
    environment: str | None = None,
    region: str | None = None,
    instance_type: str | None = None,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """
    Load metrics and instance info from the DB, aggregate per instance, and return features.

    This function:
    1. Joins Instance + Metric tables
    2. Filters to the last `lookback_days` of metrics
    3. Aggregates metrics per instance
    4. Builds numeric features + is_prod + instance_type_family encoding
    5. Builds labels using the same rule as training (avg_cpu < 20 && avg_mem < 25)

    Args:
        session: SQLAlchemy session
        lookback_days: Number of days to look back for metrics
        environment: Optional filter by environment
        region: Optional filter by region
        instance_type: Optional filter by instance_type

    Returns:
        Tuple of:
        - X: Feature DataFrame ready for model input (no instance_id, no labels)
        - y: Label Series (0 = keep, 1 = downsize)
        - meta: DataFrame with metadata columns per instance:
          (instance_id, cloud_instance_id, environment, region, instance_type, hourly_cost)
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    # Query to join Instance + Metric with all needed columns
    query = (
        session.query(
            Instance.id.label("instance_id"),
            Instance.cloud_instance_id,
            Instance.instance_type,
            Instance.environment,
            Instance.region,
            Instance.hourly_cost,
            Metric.cpu_utilization,
            Metric.mem_utilization,
            Metric.network_in_bytes,
            Metric.network_out_bytes,
            Metric.timestamp,
        )
        .join(Metric, Instance.id == Metric.instance_id)
        .filter(Metric.timestamp >= cutoff_date)
    )

    # Apply optional filters
    if environment:
        query = query.filter(Instance.environment == environment)
    if region:
        query = query.filter(Instance.region == region)
    if instance_type:
        query = query.filter(Instance.instance_type == instance_type)

    df = pd.read_sql(query.statement, session.bind)

    if len(df) == 0:
        # Return empty DataFrames with correct structure
        empty_X = pd.DataFrame()
        empty_y = pd.Series(dtype=int)
        empty_meta = pd.DataFrame(
            columns=["instance_id", "cloud_instance_id", "environment", "region", "instance_type", "hourly_cost"]
        )
        return empty_X, empty_y, empty_meta

    # Aggregate per instance
    agg_dict = {
        "cpu_utilization": ["mean", lambda x: x.quantile(0.95)],
        "mem_utilization": ["mean", lambda x: x.quantile(0.95)],
        "network_in_bytes": "mean",
        "network_out_bytes": "mean",
        "environment": "first",  # Take first (should be same for all rows)
        "instance_type": "first",  # Take first (should be same for all rows)
        "region": "first",
        "hourly_cost": "first",
        "cloud_instance_id": "first",
    }

    grouped = df.groupby("instance_id").agg(agg_dict)
    grouped.columns = [
        "avg_cpu",
        "p95_cpu",
        "avg_mem",
        "p95_mem",
        "avg_net_in_bytes",
        "avg_net_out_bytes",
        "environment",
        "instance_type",
        "region",
        "hourly_cost",
        "cloud_instance_id",
    ]

    # Reset index to make instance_id a column
    grouped = grouped.reset_index()

    # Convert network bytes to MB
    grouped["avg_net_in_mb"] = grouped["avg_net_in_bytes"] / 1e6
    grouped["avg_net_out_mb"] = grouped["avg_net_out_bytes"] / 1e6
    grouped = grouped.drop(columns=["avg_net_in_bytes", "avg_net_out_bytes"])

    # Create is_prod feature
    grouped["is_prod"] = (grouped["environment"] == "prod").astype(int)

    # Save metadata before feature engineering (include avg_cpu and avg_mem for recommendations)
    meta_df = grouped[
        ["instance_id", "cloud_instance_id", "environment", "region", "instance_type", "hourly_cost"]
    ].copy()
    # Add avg_cpu and avg_mem from the grouped DataFrame for use in recommendations
    meta_df["avg_cpu"] = grouped["avg_cpu"]
    meta_df["avg_mem"] = grouped["avg_mem"]

    # Extract instance type family
    grouped["instance_type_family"] = grouped["instance_type"].apply(
        extract_instance_type_family
    )

    # One-hot encode instance_type_family
    family_dummies = pd.get_dummies(
        grouped["instance_type_family"], prefix="family", dummy_na=False
    )
    grouped = pd.concat([grouped, family_dummies], axis=1)
    grouped = grouped.drop(columns=["instance_type_family", "instance_type", "environment"])

    # Create labels: downsize if avg_cpu < 20 AND avg_mem < 25
    grouped["label_str"] = grouped.apply(
        lambda row: "downsize"
        if (row["avg_cpu"] < 20 and row["avg_mem"] < 25)
        else "keep",
        axis=1,
    )
    grouped["label"] = (grouped["label_str"] == "downsize").astype(int)

    # Separate features and labels
    feature_cols = [
        col
        for col in grouped.columns
        if col
        not in [
            "instance_id",
            "label",
            "label_str",
            "cloud_instance_id",
            "region",
            "hourly_cost",
        ]
    ]
    X = grouped[feature_cols].copy()
    y = grouped["label"].copy()

    return X, y, meta_df

