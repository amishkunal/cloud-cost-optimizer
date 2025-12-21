"""
Simple test script to verify model loading works.
Run this from the backend directory: python3 test_load_model.py
"""

from app.ml.load_model import load_model

def main():
    print("=" * 60)
    print("Testing Model Loading")
    print("=" * 60)
    
    try:
        # Load model
        model, metadata = load_model()
        
        print("\n✓ Model loaded successfully!")
        print(f"\nModel type: {type(model)}")
        print(f"\nMetadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        
        print("\n" + "=" * 60)
        print("Model is ready to use!")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure you've run the training script first:")
        print("  python3 -m app.ml.train_model")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()





