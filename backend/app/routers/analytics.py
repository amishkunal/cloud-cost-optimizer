"""
Analytics router for Cloud Cost Optimizer.

Provides system-level performance and model metrics.
"""

import logging
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..ml.features import compute_instance_features
from ..ml.load_model import load_model
from ..models import Instance
from ..routers.cost_trends import get_total_cost_trends
from ..routers.recommendations import get_recommendations_counter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def get_analytics_summary(db: Session = Depends(get_db)) -> Dict:
    """
    Returns overall system metrics including cost reduction, model performance, etc.
    """
    try:
        # Load model metadata
        try:
            _, metadata = load_model()
            model_version = metadata.get("model_version", "unknown")
            validation_accuracy = metadata.get("validation_accuracy", 0.0)
            last_trained_at = metadata.get("trained_at", "unknown")
            training_runtime_sec = metadata.get("training_runtime_sec", None)
        except FileNotFoundError:
            model_version = "unknown"
            validation_accuracy = 0.0
            last_trained_at = "unknown"
            training_runtime_sec = None

        # Get all instances
        instances = db.query(Instance).all()
        instance_count = len(instances)

        # Compute features to determine downsizes
        X, y, meta_df = compute_instance_features(db, lookback_days=7)

        # Count downsizes and compute costs
        downsize_count = 0
        total_baseline_monthly_cost = 0.0
        total_optimized_monthly_cost = 0.0

        for instance in instances:
            hourly_cost = float(instance.hourly_cost) if instance.hourly_cost else 0.0
            if hourly_cost > 0:
                monthly_cost = hourly_cost * 24 * 30
                total_baseline_monthly_cost += monthly_cost

                # Check if this instance should be downsized
                instance_found = False
                for idx in range(len(meta_df)):
                    if int(meta_df.iloc[idx]["instance_id"]) == instance.id:
                        avg_cpu = float(meta_df.iloc[idx].get("avg_cpu", 0))
                        avg_mem = float(meta_df.iloc[idx].get("avg_mem", 0))
                        should_downsize = avg_cpu < 20 and avg_mem < 25
                        instance_found = True

                        if should_downsize:
                            downsize_count += 1
                            optimized_monthly_cost = (hourly_cost * 0.6) * 24 * 30
                        else:
                            optimized_monthly_cost = monthly_cost
                        total_optimized_monthly_cost += optimized_monthly_cost
                        break

                if not instance_found:
                    # Instance has no metrics, assume keep
                    total_optimized_monthly_cost += monthly_cost

        total_monthly_savings = total_baseline_monthly_cost - total_optimized_monthly_cost

        # Calculate per-environment breakdown
        env_costs = {}
        for instance in instances:
            hourly_cost = float(instance.hourly_cost) if instance.hourly_cost else 0.0
            if hourly_cost <= 0:
                continue
            
            env = instance.environment or "unknown"
            if env not in env_costs:
                env_costs[env] = {"baseline": 0.0, "optimized": 0.0}
            
            monthly_cost = hourly_cost * 24 * 30
            env_costs[env]["baseline"] += monthly_cost

            # Check if this instance should be downsized
            instance_found = False
            for idx in range(len(meta_df)):
                if int(meta_df.iloc[idx]["instance_id"]) == instance.id:
                    avg_cpu = float(meta_df.iloc[idx].get("avg_cpu", 0))
                    avg_mem = float(meta_df.iloc[idx].get("avg_mem", 0))
                    should_downsize = avg_cpu < 20 and avg_mem < 25
                    instance_found = True

                    if should_downsize:
                        optimized_monthly_cost = (hourly_cost * 0.6) * 24 * 30
                    else:
                        optimized_monthly_cost = monthly_cost
                    env_costs[env]["optimized"] += optimized_monthly_cost
                    break

            if not instance_found:
                # Instance has no metrics, assume keep
                env_costs[env]["optimized"] += monthly_cost

        # Format environment breakdown
        env_breakdown = [
            {
                "env": env,
                "baseline": round(costs["baseline"], 2),
                "optimized": round(costs["optimized"], 2),
            }
            for env, costs in sorted(env_costs.items())
        ]

        return {
            "instance_count": instance_count,
            "downsize_count": downsize_count,
            "total_baseline_monthly_cost": round(total_baseline_monthly_cost, 2),
            "total_optimized_monthly_cost": round(total_optimized_monthly_cost, 2),
            "total_monthly_savings": round(total_monthly_savings, 2),
            "model_version": model_version,
            "validation_accuracy": validation_accuracy,
            "last_trained_at": last_trained_at,
            "training_runtime_sec": training_runtime_sec,
            "recommendations_requests": get_recommendations_counter(),
            "env_breakdown": env_breakdown,
        }

    except Exception as e:
        logger.error(f"Error computing analytics summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error computing analytics summary: {str(e)}",
        )


@router.get("/ai_summary")
async def get_ai_summary(db: Session = Depends(get_db)):
    """
    Generate an AI-powered summary of savings trends and optimization opportunities.
    
    Uses OpenAI to analyze analytics summary and cost trends data.
    """
    # Check if OpenAI API key is configured
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI summaries are not configured (missing OPENAI_API_KEY).",
        )

    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="OpenAI client not installed. Run: pip install openai",
        )

    try:
        # Get analytics summary
        summary = get_analytics_summary(db)
        
        # Get cost trends
        trends = get_total_cost_trends(db, lookback_days=30)

        # Build context for LLM
        context = {
            "total_baseline_monthly_cost": summary["total_baseline_monthly_cost"],
            "total_optimized_monthly_cost": summary["total_optimized_monthly_cost"],
            "total_monthly_savings": summary["total_monthly_savings"],
            "instance_count": summary["instance_count"],
            "downsize_count": summary["downsize_count"],
            "downsize_rate": (summary["downsize_count"] / summary["instance_count"] * 100) if summary["instance_count"] > 0 else 0,
            "env_breakdown": summary.get("env_breakdown", []),
            "model_version": summary["model_version"],
            "validation_accuracy": summary["validation_accuracy"],
        }

        # Calculate average daily savings from trends
        if trends["days"] and len(trends["baseline_daily_cost"]) > 0:
            avg_daily_savings = sum(
                baseline - optimized
                for baseline, optimized in zip(trends["baseline_daily_cost"], trends["optimized_daily_cost"])
            ) / len(trends["baseline_daily_cost"])
            context["avg_daily_savings"] = round(avg_daily_savings, 2)

        client = AsyncOpenAI(api_key=settings.openai_api_key)

        system_prompt = (
            "You are a cloud cost optimization analyst. Provide concise, actionable insights "
            "about infrastructure cost savings and optimization opportunities. Write in a professional "
            "but accessible tone. Focus on key metrics, trends, and recommendations."
        )

        user_prompt = f"""Analyze the following cloud cost optimization data and provide a 2-3 sentence summary:

**Cost Summary:**
- Total baseline monthly cost: ${context['total_baseline_monthly_cost']:.2f}
- Total optimized monthly cost: ${context['total_optimized_monthly_cost']:.2f}
- Total monthly savings: ${context['total_monthly_savings']:.2f}
- {context['downsize_count']} out of {context['instance_count']} instances recommended for downsizing ({context['downsize_rate']:.1f}%)

**Environment Breakdown:**
{chr(10).join(f"- {env['env']}: ${env['baseline']:.2f} baseline → ${env['optimized']:.2f} optimized" for env in context['env_breakdown'])}

**Model Performance:**
- Model version: {context['model_version']}
- Validation accuracy: {context['validation_accuracy']*100:.1f}%

Provide a concise summary highlighting the most significant savings opportunities and efficiency insights."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=300,
            temperature=0.7,
        )

        summary_text = response.choices[0].message.content.strip()
        return {
            "summary": summary_text,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail=f"AI summaries are not available: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating AI summary: {str(e)}",
        )

