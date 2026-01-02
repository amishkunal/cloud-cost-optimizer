import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.ml.shap_explain import top_k_reasons_for_downsize


def test_top_k_reasons_handles_binary_outputs():
    X = pd.DataFrame(
        {
            "avg_cpu": [10, 80, 15, 70],
            "p95_cpu": [15, 95, 18, 90],
            "avg_mem": [10, 85, 20, 80],
            "p95_mem": [15, 90, 22, 88],
            "avg_net_in_mb": [0.1, 5.0, 0.2, 4.5],
            "avg_net_out_mb": [0.1, 4.0, 0.2, 3.5],
            "is_prod": [0, 1, 0, 1],
        }
    )
    y = pd.Series([1, 0, 1, 0])

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("classifier", XGBClassifier(random_state=42, eval_metric="logloss")),
        ]
    )
    model.fit(X, y)

    reasons = top_k_reasons_for_downsize(model, X, top_k=3)
    assert len(reasons) == len(X)
    assert all(isinstance(r, list) for r in reasons)
    assert all(len(r) == 3 for r in reasons)

