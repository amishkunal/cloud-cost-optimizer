"""
ML router for Cloud Cost Optimizer.

Provides ML model metadata and training information.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ..ml.load_model import load_model

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/metadata")
def get_ml_metadata() -> Dict:
    """
    Returns ML model metadata from the saved model file.

    Includes model version, training date, validation metrics, and runtime.
    """
    try:
        _, metadata = load_model()
        return {
            "model_version": metadata.get("model_version", "unknown"),
            "trained_at": metadata.get("trained_at", "unknown"),
            "validation_accuracy": metadata.get("validation_accuracy", 0.0),
            "validation_precision_downsize": metadata.get("validation_precision_downsize", 0.0),
            "validation_recall_downsize": metadata.get("validation_recall_downsize", 0.0),
            "validation_f1_downsize": metadata.get("validation_f1_downsize", 0.0),
            "training_runtime_sec": metadata.get("training_runtime_sec"),
            "train_size": metadata.get("train_size", 0),
            "val_size": metadata.get("val_size", 0),
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Model not trained yet. Please run 'python -m app.ml.train_model' first.",
        )
    except Exception as e:
        logger.error(f"Error loading model metadata: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error loading model metadata: {str(e)}",
        )





