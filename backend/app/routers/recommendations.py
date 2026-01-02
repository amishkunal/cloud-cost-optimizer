"""
Recommendations router for Cloud Cost Optimizer.

This router provides ML-driven recommendations for instance downsizing.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..llm.explanations import generate_explanation_for_recommendation
from ..ml.features import compute_instance_features
from ..ml.load_model import load_model
from ..ml.shap_explain import top_k_reasons_for_downsize
from ..schemas import RecommendationOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Simple in-memory counter for analytics
_recommendations_request_count = 0


def increment_recommendations_counter():
    """Increment the recommendations request counter."""
    global _recommendations_request_count
    _recommendations_request_count += 1


def get_recommendations_counter() -> int:
    """Get the current recommendations request count."""
    return _recommendations_request_count


def compute_projected_savings(
    hourly_cost: float | None, action: str
) -> float:
    """
    Compute projected monthly savings if downsizing.

    Args:
        hourly_cost: Current hourly cost of the instance
        action: "keep" or "downsize"

    Returns:
        Projected monthly savings in dollars
    """
    if action == "keep" or hourly_cost is None or hourly_cost <= 0:
        return 0.0

    # Assume downsize means moving to 40% cheaper instance
    projected_hourly_cost = hourly_cost * 0.6
    monthly_savings = (hourly_cost - projected_hourly_cost) * 24 * 30
    return float(monthly_savings)


# build_reasons function removed - reasons are now built inline in list_recommendations
# based on the heuristic rule that determines the action


@router.get("", response_model=List[RecommendationOut])
def list_recommendations(
    db: Session = Depends(get_db),
    min_savings: float = Query(0.0, description="Minimum projected monthly savings to include"),
    environment: str | None = Query(None, description="Filter by environment"),
    region: str | None = Query(None, description="Filter by region"),
    instance_type: str | None = Query(None, description="Filter by instance type"),
    include_shap: bool = Query(False, description="Include top feature-contribution reasons (SHAP)"),
):
    """
    Get ML-driven recommendations for all instances.

    Returns recommendations sorted by projected monthly savings (highest first).
    """
    # Increment request counter
    increment_recommendations_counter()

    try:
        # Load model
        model, metadata = load_model()
        model_version = metadata.get("model_version", "unknown")
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Model not trained yet. Please run 'python -m app.ml.train_model' first.",
        )
    except Exception as e:
        logger.error(f"Error loading model: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error loading model: {str(e)}",
        )

    try:
        # Compute features for all instances (with optional filters)
        X, y, meta_df = compute_instance_features(
            db,
            lookback_days=7,
            environment=environment,
            region=region,
            instance_type=instance_type,
        )

        if len(X) == 0:
            return []

        # Make predictions
        predictions = model.predict(X)
        probabilities = model.predict_proba(X)

        shap_reasons_by_idx = {}
        if include_shap:
            try:
                downsize_idxs = []
                for idx in range(len(X)):
                    meta_row = meta_df.iloc[idx]
                    avg_cpu = float(meta_row.get("avg_cpu", 0))
                    avg_mem = float(meta_row.get("avg_mem", 0))
                    if avg_cpu < 20 and avg_mem < 25:
                        downsize_idxs.append(idx)
                if downsize_idxs:
                    X_down = X.iloc[downsize_idxs]
                    reasons_list = top_k_reasons_for_downsize(model, X_down, top_k=3)
                    for local_i, global_idx in enumerate(downsize_idxs):
                        shap_reasons_by_idx[global_idx] = reasons_list[local_i]
            except Exception:
                shap_reasons_by_idx = {}

        # Build recommendations
        recommendations = []

        for idx in range(len(X)):
            # Get model confidence (probability for downsize class)
            prob_downsize = float(probabilities[idx][1])  # Probability of class 1 (downsize)

            # Get metadata for this instance
            meta_row = meta_df.iloc[idx].to_dict()
            instance_id = int(meta_row["instance_id"])
            hourly_cost = (
                float(meta_row["hourly_cost"]) if meta_row["hourly_cost"] is not None else None
            )

            # Get avg_cpu and avg_mem from metadata
            avg_cpu = float(meta_row.get("avg_cpu", 0))
            avg_mem = float(meta_row.get("avg_mem", 0))

            # Apply heuristic rule to determine action (not model prediction)
            if avg_cpu < 20 and avg_mem < 25:
                action = "downsize"
            else:
                action = "keep"

            # Compute savings only if action is downsize
            if action == "downsize":
                orig_hourly = hourly_cost or 0.0
                if orig_hourly > 0:
                    downsize_hourly = orig_hourly * 0.6
                    projected_savings = float((orig_hourly - downsize_hourly) * 24 * 30)
                else:
                    projected_savings = 0.0
            else:
                projected_savings = 0.0

            # Filter by min_savings if specified
            if min_savings > 0.0 and projected_savings < min_savings:
                continue

            # Build reasons based on the heuristic rule
            reasons = []
            if avg_cpu < 20:
                reasons.append(f"Average CPU utilization is low ({avg_cpu:.1f}%)")
            if avg_mem < 25:
                reasons.append(f"Average memory utilization is low ({avg_mem:.1f}%)")
            instance_environment = meta_row.get("environment")
            if instance_environment and instance_environment.lower() not in ["prod", "production"]:
                reasons.append(f"Instance is in a non-production environment ({instance_environment})")

            recommendation = RecommendationOut(
                instance_id=instance_id,
                cloud_instance_id=meta_row["cloud_instance_id"],
                environment=meta_row.get("environment"),
                region=meta_row.get("region"),
                instance_type=meta_row.get("instance_type"),
                hourly_cost=hourly_cost,
                action=action,
                confidence_downsize=prob_downsize,
                projected_monthly_savings=projected_savings,
                model_version=model_version,
                reasons=reasons,
                shap_reasons=shap_reasons_by_idx.get(idx),
            )

            recommendations.append(recommendation)

        # Sort by projected savings (highest first)
        recommendations.sort(key=lambda r: r.projected_monthly_savings, reverse=True)

        return recommendations

    except Exception as e:
        logger.error(f"Error generating recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating recommendations: {str(e)}",
        )


@router.get("/{instance_id}/llm_explanation")
async def get_llm_explanation_for_instance(
    instance_id: int,
    db: Session = Depends(get_db),
):
    """
    Get LLM-generated explanation for a specific instance recommendation.

    Returns a natural language explanation of the recommendation.
    """
    # Check if OpenAI API key is configured
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="LLM explanations are not configured (missing OPENAI_API_KEY).",
        )

    try:
        # Load model
        model, metadata = load_model()
        model_version = metadata.get("model_version", "unknown")
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Model not trained yet. Please run 'python -m app.ml.train_model' first.",
        )
    except Exception as e:
        logger.error(f"Error loading model: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error loading model: {str(e)}",
        )

    try:
        # Compute features for this specific instance
        X, y, meta_df = compute_instance_features(db, lookback_days=7)

        if len(X) == 0:
            raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found or has no metrics")

        # Find the instance in the results
        instance_idx = None
        for idx in range(len(meta_df)):
            if int(meta_df.iloc[idx]["instance_id"]) == instance_id:
                instance_idx = idx
                break

        if instance_idx is None:
            raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

        # Get model predictions for this instance
        probabilities = model.predict_proba(X)
        prob_downsize = float(probabilities[instance_idx][1])

        # Get metadata
        meta_row = meta_df.iloc[instance_idx].to_dict()
        hourly_cost = (
            float(meta_row["hourly_cost"]) if meta_row["hourly_cost"] is not None else None
        )
        avg_cpu = float(meta_row.get("avg_cpu", 0))
        avg_mem = float(meta_row.get("avg_mem", 0))

        # Apply heuristic rule
        if avg_cpu < 20 and avg_mem < 25:
            action = "downsize"
        else:
            action = "keep"

        # Compute savings
        if action == "downsize":
            orig_hourly = hourly_cost or 0.0
            if orig_hourly > 0:
                downsize_hourly = orig_hourly * 0.6
                projected_savings = float((orig_hourly - downsize_hourly) * 24 * 30)
            else:
                projected_savings = 0.0
        else:
            projected_savings = 0.0

        # Build reasons
        reasons = []
        if avg_cpu < 20:
            reasons.append(f"Average CPU utilization is low ({avg_cpu:.1f}%)")
        if avg_mem < 25:
            reasons.append(f"Average memory utilization is low ({avg_mem:.1f}%)")
        instance_environment = meta_row.get("environment")
        if instance_environment and instance_environment.lower() not in ["prod", "production"]:
            reasons.append(f"Instance is in a non-production environment ({instance_environment})")

        # Build recommendation object
        recommendation = RecommendationOut(
            instance_id=instance_id,
            cloud_instance_id=meta_row["cloud_instance_id"],
            environment=meta_row.get("environment"),
            region=meta_row.get("region"),
            instance_type=meta_row.get("instance_type"),
            hourly_cost=hourly_cost,
            action=action,
            confidence_downsize=prob_downsize,
            projected_monthly_savings=projected_savings,
            model_version=model_version,
            reasons=reasons,
        )

        # Generate LLM explanation
        try:
            llm_explanation = await generate_explanation_for_recommendation(recommendation)
        except ValueError as e:
            # ValueError means missing package or API key - return 503
            logger.error(f"LLM explanation configuration error: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=f"LLM explanations are not available: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Error generating LLM explanation: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error generating LLM explanation: {str(e)}",
            )

        return {
            "instance_id": instance_id,
            "cloud_instance_id": recommendation.cloud_instance_id,
            "llm_explanation": llm_explanation,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendation for instance {instance_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating recommendation: {str(e)}",
        )

