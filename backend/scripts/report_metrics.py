import argparse
import json
import socket
import time
from datetime import datetime, timezone
from statistics import median

import numpy as np
import pandas as pd
from sqlalchemy.exc import OperationalError
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.db import SessionLocal
from app.models import Instance, Metric, RightSizingAction


def _extract_instance_type_family(instance_type: str) -> str:
    if pd.isna(instance_type) or not instance_type:
        return "unknown"
    parts = str(instance_type).split(".")
    return parts[0] if parts else "unknown"


def compute_features_asof(session, as_of: datetime, lookback_days: int):
    from datetime import timedelta

    cutoff_date = as_of - timedelta(days=lookback_days)

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
        .filter(Metric.timestamp <= as_of)
    )

    df = pd.read_sql(query.statement, session.bind)
    if len(df) == 0:
        return pd.DataFrame(), pd.Series(dtype=int), pd.DataFrame()

    agg_dict = {
        "cpu_utilization": ["mean", lambda x: x.quantile(0.95)],
        "mem_utilization": ["mean", lambda x: x.quantile(0.95)],
        "network_in_bytes": "mean",
        "network_out_bytes": "mean",
        "environment": "first",
        "instance_type": "first",
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
    grouped = grouped.reset_index()

    grouped["avg_net_in_mb"] = grouped["avg_net_in_bytes"] / 1e6
    grouped["avg_net_out_mb"] = grouped["avg_net_out_bytes"] / 1e6
    grouped = grouped.drop(columns=["avg_net_in_bytes", "avg_net_out_bytes"])

    grouped["is_prod"] = (grouped["environment"] == "prod").astype(int)

    meta_df = grouped[
        ["instance_id", "cloud_instance_id", "environment", "region", "instance_type", "hourly_cost"]
    ].copy()
    meta_df["avg_cpu"] = grouped["avg_cpu"]
    meta_df["avg_mem"] = grouped["avg_mem"]

    grouped["instance_type_family"] = grouped["instance_type"].apply(_extract_instance_type_family)
    family_dummies = pd.get_dummies(grouped["instance_type_family"], prefix="family", dummy_na=False)
    grouped = pd.concat([grouped, family_dummies], axis=1)
    grouped = grouped.drop(columns=["instance_type_family", "instance_type", "environment"])

    grouped["label"] = ((grouped["avg_cpu"] < 20) & (grouped["avg_mem"] < 25)).astype(int)
    y = grouped["label"].copy()

    feature_cols = [
        c
        for c in grouped.columns
        if c
        not in [
            "instance_id",
            "label",
            "cloud_instance_id",
            "region",
            "hourly_cost",
        ]
    ]
    X = grouped[feature_cols].copy()
    return X, y, meta_df


def pct(n: float, d: float) -> float:
    return (n / d * 100.0) if d else 0.0


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    idx = int(q * (len(xs) - 1))
    return float(xs[idx])


def can_connect(host: str, port: int, timeout_sec: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True
    except Exception:
        return False


def http_get_timing(url: str, n: int) -> dict:
    import urllib.request

    timings_ms: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        with urllib.request.urlopen(url, timeout=5) as resp:
            _ = resp.read()
            status = getattr(resp, "status", 200)
            if int(status) >= 400:
                raise RuntimeError(f"HTTP {status} from {url}")
        timings_ms.append((time.perf_counter() - t0) * 1000.0)
    return {
        "n": n,
        "p50_ms": quantile(timings_ms, 0.50),
        "p95_ms": quantile(timings_ms, 0.95),
        "p99_ms": quantile(timings_ms, 0.99),
        "avg_ms": float(sum(timings_ms) / len(timings_ms)) if timings_ms else 0.0,
    }


def main():
    ap = argparse.ArgumentParser(description="Compute ML + system metrics for Cloud Cost Optimizer")
    ap.add_argument("--lookback-days", type=int, default=7)
    ap.add_argument("--api-base", type=str, default="http://127.0.0.1:8000")
    ap.add_argument("--api-samples", type=int, default=30)
    ap.add_argument("--no-api", action="store_true", help="Skip API latency measurements")
    ap.add_argument("--json", action="store_true", help="Output JSON only")
    args = ap.parse_args()

    try:
        db = SessionLocal()
        # Force a connection early so we can fail fast with a helpful message.
        db.connection()
    except OperationalError as e:
        msg = str(e).splitlines()[0]
        print("ERROR: Could not connect to the database.")
        print(f"Details: {msg}")
        print("")
        print("Fix:")
        print("  - Start Postgres:  docker compose up -d db")
        print("  - Or run:          ./run.sh")
        raise SystemExit(2)
    try:
        out: dict = {"generated_at": datetime.now(timezone.utc).isoformat()}

        # Dataset size
        instance_rows = int(db.query(Instance).count())
        metric_rows = int(db.query(Metric).count())
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        metric_rows_last_24h = int(db.query(Metric).filter(Metric.timestamp >= cutoff).count())

        min_ts = db.query(Metric.timestamp).order_by(Metric.timestamp.asc()).limit(1).scalar()
        max_ts = db.query(Metric.timestamp).order_by(Metric.timestamp.desc()).limit(1).scalar()
        as_of = max_ts or datetime.now(timezone.utc)
        out["data"] = {
            "instances": instance_rows,
            "metric_rows_total": metric_rows,
            "metric_rows_last_24h": metric_rows_last_24h,
            "metric_time_range": {
                "min": min_ts.isoformat() if min_ts else None,
                "max": max_ts.isoformat() if max_ts else None,
            },
        }

        # Features + labels
        X, y, meta_df = compute_features_asof(db, as_of=as_of, lookback_days=args.lookback_days)
        out["ml"] = {
            "lookback_days": args.lookback_days,
            "feature_rows": int(len(X)),
            "feature_cols": int(X.shape[1]) if len(X) else 0,
            "label_distribution": {
                "keep": int((y == 0).sum()) if len(y) else 0,
                "downsize": int((y == 1).sum()) if len(y) else 0,
                "downsize_rate_pct": pct(float((y == 1).sum()), float(len(y))) if len(y) else 0.0,
            },
        }

        # Model evaluation (holdout)
        if len(X) >= 10 and len(set(y.tolist())) == 2:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            pipeline = Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("classifier", XGBClassifier(random_state=42, eval_metric="logloss")),
                ]
            )
            t0 = time.perf_counter()
            pipeline.fit(X_train, y_train)
            train_ms = (time.perf_counter() - t0) * 1000.0

            y_pred = pipeline.predict(X_val)
            acc = float(accuracy_score(y_val, y_pred))
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_val, y_pred, labels=[1], average="binary", zero_division=0
            )

            # Inference latency on the holdout feature matrix
            timings_ms: list[float] = []
            for _ in range(200):
                t1 = time.perf_counter()
                _ = pipeline.predict_proba(X_val)
                timings_ms.append((time.perf_counter() - t1) * 1000.0)

            out["ml"]["holdout_eval"] = {
                "val_size": int(len(X_val)),
                "accuracy": acc,
                "precision_downsize": float(precision),
                "recall_downsize": float(recall),
                "f1_downsize": float(f1),
                "train_time_ms": float(train_ms),
                "inference_p95_ms": quantile(timings_ms, 0.95),
            }
        else:
            out["ml"]["holdout_eval"] = {
                "note": "Insufficient data or only one class; add more instances/metrics to compute holdout F1.",
            }

        # Projected savings (matches API logic: downsize => 40% cheaper)
        avg_cpu_by_id = {}
        avg_mem_by_id = {}
        if len(meta_df) > 0:
            for row in meta_df.itertuples(index=False):
                avg_cpu_by_id[int(row.instance_id)] = float(getattr(row, "avg_cpu", 0.0))
                avg_mem_by_id[int(row.instance_id)] = float(getattr(row, "avg_mem", 0.0))

        baseline = 0.0
        optimized = 0.0
        downsized = 0
        for inst in db.query(Instance).all():
            hc = float(inst.hourly_cost) if inst.hourly_cost else 0.0
            if hc <= 0:
                continue
            monthly = hc * 24 * 30
            baseline += monthly
            avg_cpu = avg_cpu_by_id.get(int(inst.id))
            avg_mem = avg_mem_by_id.get(int(inst.id))
            should_downsize = (avg_cpu is not None and avg_mem is not None and avg_cpu < 20 and avg_mem < 25)
            if should_downsize:
                downsized += 1
                optimized += (hc * 0.6) * 24 * 30
            else:
                optimized += monthly
        savings = baseline - optimized
        out["savings"] = {
            "baseline_monthly_usd": round(baseline, 2),
            "optimized_monthly_usd": round(optimized, 2),
            "projected_monthly_savings_usd": round(savings, 2),
            "projected_reduction_pct": round(pct(savings, baseline), 2),
            "downsized_instances": downsized,
        }

        # Action tracking outcomes
        statuses = [a.status for a in db.query(RightSizingAction).all()]
        out["actions"] = {
            "total": len(statuses),
            "verified": sum(1 for s in statuses if s == "verified"),
            "mismatch": sum(1 for s in statuses if s == "mismatch"),
            "error": sum(1 for s in statuses if s == "error"),
            "pending": sum(1 for s in statuses if s == "pending"),
        }

        # Optional API latencies (wall-clock HTTP)
        if not args.no_api:
            host = "127.0.0.1"
            port = 8000
            if can_connect(host, port):
                base = args.api_base.rstrip("/")
                out["api_latency"] = {
                    "instances": http_get_timing(f"{base}/instances", args.api_samples),
                    "recommendations": http_get_timing(f"{base}/recommendations", args.api_samples),
                }
            else:
                out["api_latency"] = {"note": "API not reachable on 127.0.0.1:8000"}

        if args.json:
            print(json.dumps(out, indent=2))
            return

        # Human-readable summary (short)
        print("Cloud Cost Optimizer — Metrics Summary")
        print("------------------------------------")
        print(f"Instances: {out['data']['instances']}, Metric rows: {out['data']['metric_rows_total']}")
        print(
            f"Projected savings: {out['savings']['projected_reduction_pct']}% "
            f"(USD {out['savings']['projected_monthly_savings_usd']}/mo)"
        )
        he = out["ml"].get("holdout_eval", {})
        if "f1_downsize" in he:
            print(f"Holdout F1 (downsize): {he['f1_downsize']:.3f}, Precision: {he['precision_downsize']:.3f}")
            print(f"Train time: {he['train_time_ms']:.1f}ms, Inference p95: {he['inference_p95_ms']:.2f}ms")
        else:
            print(f"Holdout eval: {he.get('note')}")
        if "api_latency" in out and isinstance(out["api_latency"], dict) and "instances" in out["api_latency"]:
            print(f"API p95: instances={out['api_latency']['instances']['p95_ms']:.1f}ms, "
                  f"recs={out['api_latency']['recommendations']['p95_ms']:.1f}ms")
        print(f"Actions: {out['actions']}")

    finally:
        db.close()


if __name__ == "__main__":
    main()


