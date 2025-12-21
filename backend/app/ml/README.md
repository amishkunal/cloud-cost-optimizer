# Model Loading Guide

## Loading the Trained Model

To load and use the trained model in another module (e.g., a `/recommendations` router), use the provided helper function:

### Method 1: Using the Helper Function (Recommended)

```python
from app.ml.load_model import load_model

# Load model and metadata
model, metadata = load_model()

# Model is now ready to use
print(f"Model version: {metadata['model_version']}")
print(f"Validation accuracy: {metadata['validation_accuracy']:.2%}")
```

### Method 2: Manual Loading

If you prefer to load manually:

```python
import joblib
from pathlib import Path
from app.db import SessionLocal
from app.models import Instance, Metric

# Get correct path (works from anywhere in the app)
model_dir = Path(__file__).parent.parent / "ml_models"
model_path = model_dir / "xgb_downsize_classifier.joblib"
meta_path = model_dir / "xgb_downsize_classifier_meta.json"

# Load model
model = joblib.load(model_path)

# Load metadata (optional, for reference)
import json
with open(meta_path, "r") as f:
    metadata = json.load(f)
```

### 3. Build features for a single instance

You'll need to replicate the feature engineering logic from `train_model.py`. For a single instance:

```python
def build_instance_features(instance_id: int, session, days: int = 7):
    """Build feature vector for a single instance."""
    from datetime import datetime, timedelta, timezone
    import pandas as pd
    
    # Load metrics for this instance
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    metrics = (
        session.query(Metric)
        .filter(
            Metric.instance_id == instance_id,
            Metric.timestamp >= cutoff_date
        )
        .all()
    )
    
    instance = session.query(Instance).filter(Instance.id == instance_id).first()
    
    if not metrics:
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame([{
        'cpu_utilization': float(m.cpu_utilization) if m.cpu_utilization else 0,
        'mem_utilization': float(m.mem_utilization) if m.mem_utilization else 0,
        'network_in_bytes': float(m.network_in_bytes) if m.network_in_bytes else 0,
        'network_out_bytes': float(m.network_out_bytes) if m.network_out_bytes else 0,
    } for m in metrics])
    
    # Aggregate features
    features = {
        'avg_cpu': df['cpu_utilization'].mean(),
        'p95_cpu': df['cpu_utilization'].quantile(0.95),
        'avg_mem': df['mem_utilization'].mean(),
        'p95_mem': df['mem_utilization'].quantile(0.95),
        'avg_net_in_mb': df['network_in_bytes'].mean() / 1e6,
        'avg_net_out_mb': df['network_out_bytes'].mean() / 1e6,
        'is_prod': 1 if instance.environment == "prod" else 0,
    }
    
    # Extract instance type family
    instance_type_family = instance.instance_type.split('.')[0] if instance.instance_type else "unknown"
    
    # One-hot encode family (need to match training time families)
    # You may want to store the feature column names from training
    family_features = {f'family_{instance_type_family}': 1}
    
    # Combine all features into a DataFrame with same column order as training
    # Note: You'll need to ensure all family_* columns exist (set to 0 if not present)
    # This is a simplified version - in practice, you'd want to reuse the exact
    # feature engineering function from train_model.py
    
    return pd.DataFrame([features])
```

### 4. Make predictions

```python
# Build features for instance
features_df = build_instance_features(instance_id, session)

if features_df is not None:
    # Ensure feature order matches training
    prediction = model.predict(features_df)
    probabilities = model.predict_proba(features_df)
    
    # prediction[0] = 0 (keep) or 1 (downsize)
    # probabilities[0] = [P(keep), P(downsize)]
    
    recommendation = "downsize" if prediction[0] == 1 else "keep"
    confidence = probabilities[0][prediction[0]]
```

### Recommended Approach

For production use, it's better to:

1. **Extract feature engineering into a shared module** (`app/ml/features.py`) so both training and inference use the same logic
2. **Store feature column names** in the metadata JSON so you can ensure consistent feature order
3. **Handle missing/zero values** gracefully (what if an instance has no metrics?)

### Example Router Endpoint

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
import joblib
from pathlib import Path

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.get("/instances/{instance_id}")
def get_recommendation(instance_id: int, db: Session = Depends(get_db)):
    # Load model (can be cached/loaded once at startup)
    model_path = Path(__file__).parent.parent / "ml_models" / "xgb_downsize_classifier.joblib"
    model = joblib.load(model_path)
    
    # Build features (implement this function)
    features = build_instance_features(instance_id, db)
    
    if features is None:
        raise HTTPException(404, "Insufficient metrics for recommendation")
    
    prediction = model.predict(features)[0]
    probabilities = model.predict_proba(features)[0]
    
    return {
        "instance_id": instance_id,
        "recommendation": "downsize" if prediction == 1 else "keep",
        "confidence": float(probabilities[prediction]),
        "probabilities": {
            "keep": float(probabilities[0]),
            "downsize": float(probabilities[1])
        }
    }
```

