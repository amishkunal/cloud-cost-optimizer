"""
ML training script for Cloud Cost Optimizer.

This script:
1. Loads instance metrics from the database
2. Engineers features per instance
3. Labels instances as "downsize" or "keep"
4. Trains an XGBoost classifier
5. Evaluates and saves the model
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from ..db import SessionLocal
from .features import compute_instance_features


def train_model(X: pd.DataFrame, y: pd.Series) -> Tuple[Pipeline, Dict]:
    """
    Train XGBoost classifier with feature scaling.

    Args:
        X: Feature matrix
        y: Labels (0 = keep, 1 = downsize)

    Returns:
        Tuple of (fitted pipeline, metrics dictionary)
    """
    # Split data
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Create pipeline: scale numeric features, then XGBoost
    # Note: We'll scale all features (including one-hot encoded), which is fine
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("classifier", XGBClassifier(random_state=42, eval_metric="logloss")),
        ]
    )

    # Train
    pipeline.fit(X_train, y_train)

    # Evaluate
    y_train_pred = pipeline.predict(X_train)
    y_val_pred = pipeline.predict(X_val)

    train_acc = accuracy_score(y_train, y_train_pred)
    val_acc = accuracy_score(y_val, y_val_pred)

    # Precision, recall, F1 for "downsize" class (label=1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_val, y_val_pred, labels=[1], average="binary", zero_division=0
    )

    metrics = {
        "train_size": len(X_train),
        "val_size": len(X_val),
        "train_accuracy": float(train_acc),
        "validation_accuracy": float(val_acc),
        "validation_precision_downsize": float(precision),
        "validation_recall_downsize": float(recall),
        "validation_f1_downsize": float(f1),
    }

    # Print detailed metrics
    print("\n" + "=" * 60)
    print("Training Results")
    print("=" * 60)
    print(f"\nTrain Accuracy: {train_acc:.4f}")
    print(f"Validation Accuracy: {val_acc:.4f}")
    print(f"\nValidation Metrics (Downsize Class):")
    print(f"  Precision: {metrics['validation_precision_downsize']:.4f}")
    print(f"  Recall: {metrics['validation_recall_downsize']:.4f}")
    print(f"  F1-Score: {metrics['validation_f1_downsize']:.4f}")

    print("\nConfusion Matrix (Validation):")
    cm = confusion_matrix(y_val, y_val_pred)
    print(f"                Predicted")
    print(f"              Keep  Downsize")
    print(f"Actual Keep   {cm[0,0]:4d}   {cm[0,1]:4d}")
    print(f"       Downsize {cm[1,0]:4d}   {cm[1,1]:4d}")

    print("\nClassification Report (Validation):")
    print(classification_report(y_val, y_val_pred, target_names=["keep", "downsize"]))

    return pipeline, metrics


def save_model(model: Pipeline, metrics_dict: Dict, model_dir: Path) -> None:
    """
    Save the trained model and metadata.

    Args:
        model: Trained pipeline
        metrics_dict: Evaluation metrics
        model_dir: Directory to save model artifacts
    """
    import joblib

    # Create directory if needed
    model_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    model_path = model_dir / "xgb_downsize_classifier.joblib"
    joblib.dump(model, model_path)
    print(f"\nModel saved to: {model_path}")

    # Prepare metadata
    metadata = {
        "model_version": "v0.1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_size": metrics_dict["train_size"],
        "val_size": metrics_dict["val_size"],
        "validation_accuracy": metrics_dict["validation_accuracy"],
        "validation_precision_downsize": metrics_dict["validation_precision_downsize"],
        "validation_recall_downsize": metrics_dict["validation_recall_downsize"],
        "validation_f1_downsize": metrics_dict["validation_f1_downsize"],
        "training_runtime_sec": metrics_dict.get("training_runtime_sec"),
    }

    # Save metadata
    meta_path = model_dir / "xgb_downsize_classifier_meta.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved to: {meta_path}")


def main():
    """Main training workflow."""
    print("=" * 60)
    print("Cloud Cost Optimizer - ML Model Training")
    print("=" * 60)

    # Setup
    session = SessionLocal()
    model_dir = Path(__file__).parent.parent / "ml_models"

    try:
        # Load data and build features
        print("\nLoading instance metrics and engineering features (last 7 days)...")
        X, y, meta_df = compute_instance_features(session, lookback_days=7)

        if len(X) == 0:
            print("ERROR: No metrics found in the database.")
            return

        print(f"Loaded {len(meta_df)} instances with features")

        print(f"Feature matrix shape: {X.shape}")
        print(f"Number of instances: {len(X)}")

        # Check if we have enough data
        if len(X) < 10:
            print(f"\nERROR: Insufficient data. Need at least 10 instances, got {len(X)}")
            return

        # Check class distribution
        class_counts = y.value_counts()
        print(f"\nClass distribution:")
        print(f"  Keep (0): {class_counts.get(0, 0)}")
        print(f"  Downsize (1): {class_counts.get(1, 0)}")

        if len(class_counts) < 2:
            print("\nERROR: All instances have the same label. Cannot train model.")
            return

        # Train model
        print("\nTraining XGBoost classifier...")
        train_start_time = time.time()
        model, metrics = train_model(X, y)
        train_end_time = time.time()
        training_runtime_sec = train_end_time - train_start_time

        # Add training runtime to metrics
        metrics["training_runtime_sec"] = float(training_runtime_sec)

        # Save model
        print("\nSaving model...")
        save_model(model, metrics, model_dir)

        print("\n" + "=" * 60)
        print("Training completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR during training: {e}")
        import traceback

        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    main()

