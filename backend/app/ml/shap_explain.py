from __future__ import annotations

import threading
from typing import List

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

_lock = threading.Lock()
_explainer_cache: dict[int, object] = {}


def _get_explainer(classifier) -> object:
    key = id(classifier)
    with _lock:
        cached = _explainer_cache.get(key)
        if cached is not None:
            return cached
        import shap

        explainer = shap.TreeExplainer(classifier)
        _explainer_cache[key] = explainer
        return explainer


def _reason_for_feature(name: str, value: float) -> str:
    if name == "p95_cpu":
        return f"Low P95 CPU utilization ({value:.1f}%)" if value < 20 else f"High P95 CPU utilization ({value:.1f}%)"
    if name == "avg_cpu":
        return f"Low avg CPU utilization ({value:.1f}%)" if value < 20 else f"High avg CPU utilization ({value:.1f}%)"
    if name == "p95_mem":
        return f"Low P95 memory utilization ({value:.1f}%)" if value < 25 else f"High P95 memory utilization ({value:.1f}%)"
    if name == "avg_mem":
        return f"Low avg memory utilization ({value:.1f}%)" if value < 25 else f"High avg memory utilization ({value:.1f}%)"
    if name == "avg_net_in_mb":
        return f"Low inbound network ({value:.2f} MB)" if value < 1 else f"High inbound network ({value:.2f} MB)"
    if name == "avg_net_out_mb":
        return f"Low outbound network ({value:.2f} MB)" if value < 1 else f"High outbound network ({value:.2f} MB)"
    if name == "is_prod":
        return "Non-production environment" if value < 0.5 else "Production environment"
    if name.startswith("family_") and value >= 0.5:
        return f"Instance family: {name.replace('family_', '')}"
    return name.replace("_", " ")


def top_k_reasons_for_downsize(
    pipeline: Pipeline, X: pd.DataFrame, top_k: int = 3
) -> List[List[str]]:
    if len(X) == 0:
        return []

    if not hasattr(pipeline, "named_steps"):
        raise ValueError("Expected a scikit-learn Pipeline model")

    scaler = pipeline.named_steps.get("scaler")
    classifier = pipeline.named_steps.get("classifier")
    if scaler is None or classifier is None:
        raise ValueError("Pipeline is missing scaler/classifier steps")

    X_scaled = scaler.transform(X)
    explainer = _get_explainer(classifier)
    shap_values = explainer.shap_values(X_scaled)
    sv = np.asarray(shap_values)
    if sv.ndim != 2:
        sv = sv.reshape(len(X), -1)

    feature_names = list(X.columns)
    X_vals = X.to_numpy(dtype=float, copy=False)

    all_reasons: List[List[str]] = []
    for i in range(len(X)):
        row_sv = sv[i]
        order = np.argsort(np.abs(row_sv))[::-1]
        reasons: List[str] = []
        for j in order:
            name = feature_names[int(j)]
            val = float(X_vals[i, int(j)])
            reason = _reason_for_feature(name, val)
            if reason and reason not in reasons:
                reasons.append(reason)
            if len(reasons) >= top_k:
                break
        all_reasons.append(reasons)

    return all_reasons


