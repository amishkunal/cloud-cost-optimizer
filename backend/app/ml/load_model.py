"""
Helper module to load the trained XGBoost model.

This module provides a convenient function to load the model and metadata
from the correct location, regardless of where it's called from.
"""

import json
from pathlib import Path
from typing import Dict, Tuple

import joblib
from sklearn.pipeline import Pipeline


def get_model_path() -> Path:
    """
    Get the absolute path to the model directory.
    
    This works regardless of where the code is called from.
    """
    # Get the directory where this module is located
    ml_dir = Path(__file__).parent
    # Go up one level to app/, then into ml_models/
    model_dir = ml_dir.parent / "ml_models"
    return model_dir


def load_model() -> Tuple[Pipeline, Dict]:
    """
    Load the trained XGBoost model and its metadata.
    
    Returns:
        Tuple of (model, metadata_dict)
        
    Raises:
        FileNotFoundError: If model files don't exist
    """
    model_dir = get_model_path()
    model_path = model_dir / "xgb_downsize_classifier.joblib"
    meta_path = model_dir / "xgb_downsize_classifier_meta.json"
    
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model file not found at {model_path}. "
            "Run `python -m app.ml.train_model` first."
        )
    
    if not meta_path.exists():
        raise FileNotFoundError(
            f"Metadata file not found at {meta_path}. "
            "Run `python -m app.ml.train_model` first."
        )
    
    # Load model
    model = joblib.load(model_path)
    
    # Load metadata
    with open(meta_path, "r") as f:
        metadata = json.load(f)
    
    return model, metadata


# Example usage (for testing)
if __name__ == "__main__":
    print("Loading model...")
    model, metadata = load_model()
    print(f"Model loaded successfully!")
    print(f"Model type: {type(model)}")
    print(f"\nMetadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")





