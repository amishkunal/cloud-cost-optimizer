"""
Example script showing how to load and use the trained model.

This demonstrates how to:
1. Load the model
2. Build features for an instance
3. Make predictions
"""

from app.ml.load_model import load_model
from app.ml.train_model import load_instance_metrics, build_features
from app.db import SessionLocal


def example_predict_single_instance(instance_id: int):
    """Example: Make prediction for a single instance."""
    # Load model
    print("Loading model...")
    model, metadata = load_model()
    print(f"Model loaded (version {metadata['model_version']})")
    
    # Load data for this instance
    session = SessionLocal()
    try:
        # Get all metrics (this returns all instances)
        df = load_instance_metrics(session, days=7)
        
        # Filter to just this instance
        instance_df = df[df['instance_id'] == instance_id]
        
        if len(instance_df) == 0:
            print(f"No metrics found for instance {instance_id}")
            return
        
        # Build features (this aggregates per instance)
        X, y = build_features(instance_df)
        
        # Get the row for this instance
        instance_features = X[X.index == 0]  # After aggregation, index may differ
        
        if len(instance_features) == 0:
            print(f"Could not build features for instance {instance_id}")
            return
        
        # Make prediction
        prediction = model.predict(instance_features)[0]
        probabilities = model.predict_proba(instance_features)[0]
        
        recommendation = "downsize" if prediction == 1 else "keep"
        confidence = probabilities[prediction]
        
        print(f"\nInstance {instance_id} Recommendation:")
        print(f"  Action: {recommendation}")
        print(f"  Confidence: {confidence:.2%}")
        print(f"  Probabilities: Keep={probabilities[0]:.2%}, Downsize={probabilities[1]:.2%}")
        
    finally:
        session.close()


def example_predict_all_instances():
    """Example: Make predictions for all instances."""
    # Load model
    print("Loading model...")
    model, metadata = load_model()
    print(f"Model loaded (version {metadata['model_version']})")
    
    # Load and build features for all instances
    session = SessionLocal()
    try:
        df = load_instance_metrics(session, days=7)
        X, y = build_features(df)
        
        # Make predictions for all instances
        predictions = model.predict(X)
        probabilities = model.predict_proba(X)
        
        print(f"\nPredictions for {len(X)} instances:")
        print("-" * 60)
        for idx, (pred, prob) in enumerate(zip(predictions, probabilities)):
            recommendation = "downsize" if pred == 1 else "keep"
            confidence = prob[pred]
            print(f"Instance {idx+1}: {recommendation:8s} (confidence: {confidence:.2%})")
        
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Model Usage Examples")
    print("=" * 60)
    
    # Example 1: Predict for all instances
    print("\nExample 1: Predict for all instances")
    print("-" * 60)
    example_predict_all_instances()
    
    # Example 2: Predict for a specific instance
    # Uncomment and provide an instance ID:
    # print("\nExample 2: Predict for instance 1")
    # print("-" * 60)
    # example_predict_single_instance(1)





