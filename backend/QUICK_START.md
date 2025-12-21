# Quick Start: Loading and Using the ML Model

## Loading the Model from Python REPL

If you're in the Python REPL and want to load the model, you need to set up the Python path correctly:

### Option 1: From the backend directory (Recommended)

```bash
cd backend
python3
```

Then in Python:
```python
from app.ml.load_model import load_model

model, metadata = load_model()
print(f"Model version: {metadata['model_version']}")
```

### Option 2: From any directory (using absolute path)

```python
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path("/Users/amish.kunal/cloud-cost-optimizer/backend")
sys.path.insert(0, str(backend_dir))

from app.ml.load_model import load_model

model, metadata = load_model()
```

### Option 3: Using PYTHONPATH environment variable

```bash
cd /Users/amish.kunal/cloud-cost-optimizer/backend
export PYTHONPATH=$PWD
python3
```

Then:
```python
from app.ml.load_model import load_model
model, metadata = load_model()
```

## Loading from a Script or Module

When loading from within your FastAPI app (like in a router), the import works automatically because the app is already configured:

```python
# In app/routers/recommendations.py
from app.ml.load_model import load_model

def get_recommendation(instance_id: int):
    model, metadata = load_model()
    # Use model...
```

## Quick Test

Run the test script:
```bash
cd backend
python3 test_load_model.py
```

This will verify the model loads correctly.





