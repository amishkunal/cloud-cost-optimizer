"""
LLM module for generating natural language explanations of recommendations.
"""

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from ..schemas import RecommendationOut

logger = logging.getLogger(__name__)

# Cache file path
CACHE_DB_PATH = Path(__file__).parent.parent.parent / "llm_cache.db"
CACHE_TTL_DAYS = 7


def _init_cache_db():
    """Initialize the SQLite cache database."""
    conn = sqlite3.connect(str(CACHE_DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_cache (
            instance_id INTEGER PRIMARY KEY,
            explanation TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


def _get_cached_explanation(instance_id: int) -> Optional[str]:
    """Get cached explanation if it exists and is not expired."""
    try:
        if not CACHE_DB_PATH.exists():
            return None

        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.execute(
            "SELECT explanation, created_at FROM llm_cache WHERE instance_id = ?",
            (instance_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            explanation, created_at_str = row
            created_at = datetime.fromisoformat(created_at_str)
            age = datetime.now(timezone.utc) - created_at.replace(tzinfo=timezone.utc)
            if age < timedelta(days=CACHE_TTL_DAYS):
                return explanation
            else:
                # Expired, remove from cache
                _clear_cached_explanation(instance_id)
        return None
    except Exception as e:
        logger.warning(f"Error reading from cache: {e}")
        return None


def _cache_explanation(instance_id: int, explanation: str):
    """Cache an explanation."""
    try:
        _init_cache_db()
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO llm_cache (instance_id, explanation, created_at) VALUES (?, ?, ?)",
            (instance_id, explanation, now),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Error writing to cache: {e}")


def _clear_cached_explanation(instance_id: int):
    """Clear a cached explanation."""
    try:
        if not CACHE_DB_PATH.exists():
            return
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        conn.execute("DELETE FROM llm_cache WHERE instance_id = ?", (instance_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Error clearing cache: {e}")


async def generate_explanation_for_recommendation(rec: RecommendationOut) -> str:
    """
    Uses OpenAI API to generate a richer natural-language explanation for a single recommendation.
    Implements caching to avoid repeated API calls for the same instance.

    Args:
        rec: RecommendationOut object with all recommendation details

    Returns:
        Natural language explanation string (2-4 sentences)

    Raises:
        Exception if OpenAI API call fails
    """
    # Check cache first
    cached = _get_cached_explanation(rec.instance_id)
    if cached:
        logger.debug(f"Returning cached explanation for instance {rec.instance_id}")
        return cached

    # Generate new explanation
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise ValueError("OpenAI client not installed. Run: pip install openai")

    try:
        from ..config import settings

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Build context from recommendation
        context = {
            "action": rec.action,
            "cloud_instance_id": rec.cloud_instance_id,
            "instance_type": rec.instance_type or "unknown",
            "environment": rec.environment or "unknown",
            "region": rec.region or "unknown",
            "hourly_cost": rec.hourly_cost,
            "projected_monthly_savings": rec.projected_monthly_savings,
            "confidence_downsize": rec.confidence_downsize,
            "reasons": rec.reasons,
        }

        system_prompt = (
            "You are a cloud cost optimization assistant. Explain the reasoning behind "
            "optimization recommendations for compute instances in simple, FinOps-friendly language. "
            "Keep explanations concise (2-4 sentences) and focus on cost savings and resource utilization."
        )

        # Format hourly_cost safely
        hourly_cost_str = (
            f"${context['hourly_cost']:.3f}/hr" if context['hourly_cost'] is not None else "unknown"
        )

        user_prompt = f"""Recommendation details:
- Action: {context['action']}
- Instance: {context['cloud_instance_id']} ({context['instance_type']})
- Environment: {context['environment']}, Region: {context['region']}
- Current hourly cost: {hourly_cost_str}
- Projected monthly savings: ${context['projected_monthly_savings']:.2f}
- Downsize confidence: {context['confidence_downsize']*100:.1f}%
- Reasons: {', '.join(context['reasons']) if context['reasons'] else 'None'}

Provide a clear, concise explanation of this recommendation."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.7,
        )

        explanation = response.choices[0].message.content.strip()
        
        # Cache the explanation
        _cache_explanation(rec.instance_id, explanation)
        
        return explanation

    except ValueError:
        # Re-raise ValueError (for missing API key or missing package)
        raise
    except Exception as e:
        error_str = str(e)
        # Check for invalid API key errors
        if "invalid_api_key" in error_str or "401" in error_str or "Incorrect API key" in error_str:
            raise ValueError("Invalid OpenAI API key. Please check your API key in backend/.env")
        logger.error(f"Error generating LLM explanation: {e}", exc_info=True)
        raise

